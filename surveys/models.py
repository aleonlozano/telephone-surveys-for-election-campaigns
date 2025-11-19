from django.db import models

class Campaign(models.Model):
    name = models.CharField('Nombre de la campaña', max_length=200)
    description = models.TextField('Descripción', blank=True)
    candidate_name = models.CharField('Nombre del candidato', max_length=200)
    is_active = models.BooleanField('Activa', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Campaña'
        verbose_name_plural = 'Campañas'

    def __str__(self):
        return self.name

class Contact(models.Model):
    name = models.CharField('Nombre', max_length=200, blank=True)
    phone_number = models.CharField('Número telefónico', max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'

    def __str__(self):
        return f"{self.name or self.phone_number} ({self.phone_number})"

class Call(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('calling', 'Llamando'),
        ('answered', 'Contestada'),
        ('failed', 'Fallida'),
        ('completed', 'Completada'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='calls')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls')
    status = models.CharField('Estado', max_length=20, choices=STATUS_CHOICES, default='pending')
    twilio_sid = models.CharField('SID de Twilio', max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    preference = models.CharField('Preferencia declarada', max_length=200, blank=True)
    loyalty_score = models.IntegerField('Puntaje de lealtad', null=True, blank=True)
    last_twilio_status = models.CharField('Último estado de Twilio', max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Llamada'
        verbose_name_plural = 'Llamadas'

    def __str__(self):
        return f"Llamada a {self.contact} ({self.campaign})"

class Response(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='responses')
    question_text = models.TextField('Pregunta')
    answer_raw = models.TextField('Respuesta cruda', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Respuesta'
        verbose_name_plural = 'Respuestas'

    def __str__(self):
        return f"Respuesta de {self.call.contact}"
