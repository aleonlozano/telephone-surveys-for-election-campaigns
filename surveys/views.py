from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.base.exceptions import TwilioRestException

import requests

from .models import Campaign, Contact, Call, Response
from .forms import CampaignForm, ContactForm


def dashboard(request):
    campaigns_count = Campaign.objects.count()
    contacts_count = Contact.objects.count()
    calls_count = Call.objects.count()
    calls_by_status = Call.objects.values('status').annotate(total=Count('id'))
    return render(request, 'surveys/dashboard.html', {
        'campaigns_count': campaigns_count,
        'contacts_count': contacts_count,
        'calls_count': calls_count,
        'calls_by_status': calls_by_status,
    })


def campaign_list(request):
    campaigns = Campaign.objects.all().order_by('-created_at')
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('surveys:campaign_list')
    else:
        form = CampaignForm()
    return render(request, 'surveys/campaign_list.html', {
        'campaigns': campaigns,
        'form': form,
    })


def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    calls = campaign.calls.select_related('contact').all().order_by('-created_at')
    return render(request, 'surveys/campaign_detail.html', {
        'campaign': campaign,
        'calls': calls,
    })


def contact_list(request):
    contacts = Contact.objects.all().order_by('-created_at')
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('surveys:contact_list')
    else:
        form = ContactForm()
    return render(request, 'surveys/contact_list.html', {
        'contacts': contacts,
        'form': form,
    })


def call_list(request):
    calls = Call.objects.select_related('campaign', 'contact').all().order_by('-created_at')[:200]
    return render(request, 'surveys/call_list.html', {'calls': calls})


def _get_twilio_client():
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_FROM_NUMBER:
        raise RuntimeError("Configura TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_FROM_NUMBER en las variables de entorno.")
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def launch_campaign(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method != 'POST':
        return HttpResponseBadRequest("Método no permitido")

    contacts = Contact.objects.all()
    client = _get_twilio_client()

    for contact in contacts:
        call = Call.objects.create(
            campaign=campaign,
            contact=contact,
            status='pending',
        )
        callback_url = request.build_absolute_uri(
            reverse('surveys:twilio_call_webhook', args=[call.id])
        )

        # AQUÍ ES DONDE LLAMAMOS A TWILIO:
        tw_call = client.calls.create(
            to=contact.phone_number,
            from_=settings.TWILIO_FROM_NUMBER,
            url=callback_url,
        )

        call.twilio_sid = tw_call.sid
        call.status = 'calling'
        call.started_at = timezone.now()
        call.save()

    return redirect('surveys:campaign_detail', pk=campaign.pk)


def _update_call_basic_info(call, request):
    """Actualiza campos básicos de la llamada a partir del POST de Twilio."""
    twilio_sid = request.POST.get('CallSid', '')
    call_status = request.POST.get('CallStatus', '')

    if twilio_sid and not call.twilio_sid:
        call.twilio_sid = twilio_sid

    if call_status:
        call.last_twilio_status = call_status
        if call_status == 'completed' and call.status != 'completed':
            call.status = 'completed'
            call.ended_at = timezone.now()

    call.save()


def _get_interaction_inputs(request):
    """Extrae Digits y SpeechResult del request."""
    digits = request.POST.get('Digits')
    speech = request.POST.get('SpeechResult')
    return digits, speech


def _should_ask_initial_question(existing_responses, digits, speech):
    """Determina si aún no se ha hecho la pregunta (primera interacción)."""
    return existing_responses == 0 and not (digits or speech)


def _build_question_gather(call):
    """Construye el Gather con la pregunta principal de la encuesta."""
    gather = Gather(
        input='dtmf speech',
        num_digits=1,  # permite que también responda 1,2,3 por teclado
        action=reverse('surveys:twilio_call_webhook', args=[call.id]),
        method='POST',
        timeout=8,
        language='es-ES',
    )
    question = (
        f"Hola, le llamamos para una breve encuesta ciudadana. "
        f"Pensando en las próximas elecciones, ¿qué tan decidido está a votar por {call.campaign.candidate_name}? "
        "Si está totalmente decidido, diga sí o marque 1. "
        "Si lo está considerando pero no está seguro, diga dudoso o marque 2. "
        "Si no piensa votar por esta persona, diga no o marque 3."
    )
    gather.say(question, language='es-ES')
    return gather


def _append_no_response_fallback(response_obj):
    """Mensaje de fallback cuando no hay respuesta en el Gather inicial."""
    response_obj.say("No recibimos respuesta. Gracias por su tiempo. Hasta luego.", language='es-ES')
    response_obj.hangup()


def _interpret_preference(call, digits, speech):
    """
    Interpreta la respuesta del usuario (por teclado o voz) y devuelve:
    (preference, loyalty_score, answer_raw).
    """
    preference = None
    loyalty_score = None
    answer_raw = ""

    if digits:
        answer_raw = digits
        if digits == '1':
            preference = f"A favor de {call.campaign.candidate_name}"
            loyalty_score = 3
        elif digits == '2':
            preference = f"Dudoso frente a {call.campaign.candidate_name}"
            loyalty_score = 2
        elif digits == '3':
            preference = f"En contra de {call.campaign.candidate_name}"
            loyalty_score = 1
        else:
            preference = "Respuesta inválida por teclado"
    elif speech:
        answer_raw = speech
        normalized = speech.lower()
        if "sí" in normalized or "si" in normalized:
            preference = f"A favor de {call.campaign.candidate_name}"
            loyalty_score = 3
        elif "no" in normalized:
            preference = f"En contra de {call.campaign.candidate_name}"
            loyalty_score = 1
        elif "dudoso" in normalized or "indecis" in normalized:
            preference = f"Dudoso frente a {call.campaign.candidate_name}"
            loyalty_score = 2
        else:
            preference = f"Respuesta de voz no clara: {speech}"

    return preference, loyalty_score, answer_raw


def _handle_interpreted_response(call, preference, loyalty_score, answer_raw, response_obj):
    """
    Actualiza la llamada y las respuestas en función de la interpretación,
    y añade el mensaje de cierre al TwiML.
    """
    if preference is None:
        response_obj.say("No se recibió una respuesta válida. Gracias por su tiempo.", language='es-ES')
        return

    Response.objects.create(
        call=call,
        question_text="Nivel de decisión frente al candidato",
        answer_raw=answer_raw,
    )
    call.preference = preference
    call.loyalty_score = loyalty_score
    call.status = 'completed'
    call.ended_at = timezone.now()
    call.save()

    response_obj.say("Gracias por responder. Que tenga un buen día.", language='es-ES')


@csrf_exempt
def twilio_call_webhook(request, call_id):
    """Webhook de Twilio para controlar el flujo de la llamada de encuesta."""
    call = get_object_or_404(Call, pk=call_id)

    # 1) Actualizar info básica de la llamada (sid, estado, timestamps)
    _update_call_basic_info(call, request)

    response_obj = VoiceResponse()

    # 2) Determinar si es la primera interacción o ya tenemos respuesta
    existing_responses = call.responses.count()
    digits, speech = _get_interaction_inputs(request)

    # 2.a) Primera vez: hacer la pregunta y esperar respuesta (voz o DTMF)
    if _should_ask_initial_question(existing_responses, digits, speech):
        gather = _build_question_gather(call)
        response_obj.append(gather)
        _append_no_response_fallback(response_obj)
        return HttpResponse(str(response_obj), content_type='text/xml')

    # 2.b) Ya tenemos alguna respuesta: interpretarla y actualizar la llamada
    preference, loyalty_score, answer_raw = _interpret_preference(call, digits, speech)
    _handle_interpreted_response(call, preference, loyalty_score, answer_raw, response_obj)

    # 3) Cerrar la llamada
    response_obj.hangup()
    return HttpResponse(str(response_obj), content_type='text/xml')
