# Panel de encuestas telefónicas con Django + Twilio

Este proyecto es un **panel web en Django** para lanzar **llamadas telefónicas automáticas** usando **Twilio Programmable Voice**, hacer una **pregunta de encuesta** y registrar la respuesta del encuestado (por teclado o por voz) junto con un **puntaje de lealtad**.

## 🧱 Tecnologías usadas

- **Python 3.11+**
- **Django** (backend y panel web)
- **Twilio Python SDK** (`twilio`)
- **Twilio Programmable Voice**
- **TwiML** (Twilio Markup Language) para controlar la llamada
- **SQLite** como base de datos por defecto
- **python-dotenv** para cargar variables de entorno desde `.env`
- **ngrok** para exponer el servidor local a Twilio durante el desarrollo

---

## 🧩 Conceptos clave del flujo

- El módulo Django **no llama directamente** al teléfono:  
  le pide a **Twilio** que haga la llamada vía `client.calls.create(...)`.

- Twilio, cuando la llamada es contestada, hace peticiones HTTP (**webhooks**) a tu servidor:
  - Primera vez: pregunta “¿qué hago ahora?”  
  - Tu servidor responde con **TwiML** (XML) que dice:
    - qué texto leer (`<Say>`)
    - y que espere una respuesta (`<Gather input="dtmf speech">`).

- Cuando el usuario responde (voz o teclas), Twilio vuelve a llamar al webhook:
  - Te envía `Digits` (teclas) o `SpeechResult` (texto reconocido).
  - Django procesa eso, lo guarda en la BD y devuelve otro TwiML de cierre (`Gracias… <Hangup>`).

---

## 🗂 Estructura del proyecto

```text
django_twilio_survey/
├─ survey_project/
│  ├─ settings.py        # Configuración del proyecto (Django, Twilio, ngrok, etc.)
│  ├─ urls.py            # Rutas principales
│  └─ ...
├─ surveys/
│  ├─ models.py          # Campaign, Contact, Call, Response
│  ├─ views.py           # Lógica del panel + webhook Twilio
│  ├─ forms.py           # Formularios para campañas y contactos
│  ├─ urls.py            # Rutas de la app
│  ├─ templates/
│  │  └─ surveys/
│  │     ├─ dashboard.html
│  │     ├─ campaign_list.html
│  │     ├─ campaign_detail.html
│  │     ├─ contact_list.html
│  │     └─ call_list.html
│  └─ admin.py           # Registro en el admin de Django
├─ .env                  # Variables de entorno (NO subir a git)
├─ requirements.txt
├─ manage.py
└─ README.md

Modelos principales:
	•	Campaign → campaña de encuesta (nombre, candidato, descripción, activa).
	•	Contact → encuestados (nombre, número de teléfono en formato E.164, ej: +573001112233).
	•	Call → una llamada realizada a un contacto en el contexto de una campaña (estado, sid de Twilio, preferencia, lealtad).
	•	Response → respuestas crudas por llamada (detalles de Digits/SpeechResult).

⸻
```

## ✅ Requisitos previos

Antes de ejecutar el proyecto, necesitas:
	1.	Python 3.11+ instalado.
	2.	Una cuenta en Twilio (puede ser Trial, pero tendrá:
	•	mensaje en inglés de “Trial Account” al inicio de cada llamada,
	•	restricciones de números de destino,
	•	necesidad de verificar los números a los que llamas).
	3.	ngrok instalado (para exponer tu localhost a internet).
	4.	(Opcional pero recomendable) virtualenv/venv para aislar dependencias.

⸻

## 🔐 Configuración de Twilio
	1.	En tu Twilio Console:
	•	Copia tu Account SID y Auth Token.
	2.	Compra (o asegúrate de tener) un número Twilio con capacidad de voz (Voice):
	•	Consola → Phone Numbers → Manage → Buy a number / Active numbers.
	3.	Si tu cuenta es Trial:
	•	Verifica el número de destino (tu celular) como Verified Caller ID.
	•	Habilita permisos de voz hacia Colombia (+57) en:
	•	Voice → Settings → Geo Permissions.

⸻

## ⚙️ Archivo .env

En la raíz del proyecto crea un archivo .env (si no existe) con este formato:
```
DJANGO_SECRET_KEY=pon_aqui_una_secret_key_segura
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
NGROK_HOST=tu-subdominio.ngrok-free.dev
```
- DJANGO_SECRET_KEY
Genera una clave aleatoria con:

```python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"```


- TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN

  - Desde la consola de Twilio (Dashboard → Project Info).
  

- TWILIO_FROM_NUMBER
  - El número que te asignó Twilio, con + y código de país.


- NGOK_HOST
  - Solo el host de ngrok, sin https://.
Ejemplo: si ngrok te da
https://enneadic-jere-splashingly.ngrok-free.dev,
pones:
  
```NGROK_HOST=enneadic-jere-splashingly.ngrok-free.dev```


⸻

## 🛠 Instalación y puesta en marcha

### 1. Crear y activar entorno virtual

En la carpeta del proyecto:

```python -m venv .venv source .venv/bin/activate```      # macOS / Linux

```# .venv\Scripts\activate```       # Windows (PowerShell / CMD)

### 2. Instalar dependencias

```pip install -r requirements.txt```

### 3. Aplicar migraciones

```python manage.py makemigrations```
```python manage.py migrate```

### 4. Crear superusuario (admin)

```python manage.py createsuperuser```

- Sigue el asistente para usuario, email y contraseña.

### 5. Levantar el servidor de desarrollo

```python manage.py runserver 0.0.0.0:8000```

El panel estará accesible en:
- http://127.0.0.1:8000/ (local)
- Pero para Twilio usaremos la URL pública de ngrok (ver siguiente sección).

⸻

### 🌍 Exponer el servidor con ngrok

En otra terminal (fuera del venv está bien):

```ngrok http 8000```

ngrok mostrará algo así:

```Forwarding  https://test-test-splashingly.ngrok-free.dev -> http://localhost:8000```

#### 1.	Copia el dominio de ngrok sin protocolo y colócalo en NGROK_HOST del .env:

```NGROK_HOST=test-test-splashingly.ngrok-free.dev```

#### 2.	Asegúrate de que settings.py incluye ese host en CSRF_TRUSTED_ORIGINS mediante NGROK_HOST (esto ya viene preparado en el proyecto).
#### 3.	Reinicia el servidor de Django para que tome el nuevo .env:

```python manage.py runserver 0.0.0.0:8000```

#### 4. A partir de ahora, entra al panel siempre por la URL de ngrok, por ejemplo:

https://test-test-splashingly.ngrok-free.dev/



⸻

### 📊 Flujo para probar una campaña de encuesta
#### 1.	Entra al panel:

https://TU_NGROK_HOST/campaigns/


#### 2.	Crear contactos:
  - Menú: Contactos.
    - Formulario a la derecha: añade nombre y número en formato E.164, ej: +5730011122xx.
    - Guarda.
#### 3.	Crear una campaña:
  - Menú: Campañas.
    - En “Nueva campaña”: nombre, descripción, nombre del candidato, activa = Sí.
    - Guarda.
#### 4.	Lanzar llamadas:
  - Haz clic en “Ver” en la fila de la campaña. 
    - En el detalle, pulsa “Lanzar llamadas a todos los contactos”. 
    - Se crearán registros Call y se llamará a Twilio para cada contacto.
#### 5.	Responder la llamada:
  - El teléfono configurado sonará desde tu número Twilio.
      - Oirás:
    - Primero: mensaje obligatorio de cuenta Trial (en inglés, añadido por Twilio).
    - Después: tu mensaje en español con la pregunta de encuesta.
    - Responde:
    - Por teclado (1, 2, 3), o
    - Por voz (“sí”, “no”, “dudoso”).
#### 6.	Ver resultados:
  - Menú: Campañas → “Ver” en tu campaña.
      - Abajo verás la tabla de llamadas con:
      - Estado (pending, calling, completed…),
      - Preferencia,
      - Puntaje de lealtad.
      - También puedes ver todas las llamadas en el menú Llamadas.

⸻

### 🧠 ¿Dónde se personaliza la pregunta y la lógica de respuesta?

Todo el flujo de la llamada está en:

```surveys/views.py```

Función clave: ```twilio_call_webhook```.

#### Ahí encontrarás:
```
question = (
    f"Hola, le llamamos para una breve encuesta ciudadana. "
    f"Pensando en las próximas elecciones, ¿qué tan decidido está a votar por {call.campaign.candidate_name}? "
    "Si está totalmente decidido, diga sí o marque 1. "
    "Si lo está considerando pero no está seguro, diga dudoso o marque 2. "
    "Si no piensa votar por esta persona, diga no o marque 3."
)
gather.say(question, language='es-ES')
```

- Cambia el texto de question para ajustar el guion de tu encuesta.
- Todo se reproduce mediante TTS (<Say>) en español.

Y la lógica de cómo interpretar la respuesta:

```
digits = request.POST.get('Digits')

speech = request.POST.get('SpeechResult')

if digits:
    if digits == '1':
        preference = f"A favor de {call.campaign.candidate_name}"
        loyalty_score = 3
    elif digits == '2':
        preference = f"Dudoso frente a {call.campaign.candidate_name}"
        loyalty_score = 2
    elif digits == '3':
        preference = f"En contra de {call.campaign.candidate_name}"
        loyalty_score = 1
    ...
elif speech:
    normalized = speech.lower()
    if "sí" in normalized or "si" in normalized:
        preference = ...
    elif "no" in normalized:
        preference = ...
    elif "dudoso" in normalized or "indecis" in normalized:
        preference = ...
    ...
```
#### Ahí puedes:
  - Cambiar palabras clave para voz.
  - Ajustar la lógica de puntaje.
  - Guardar más información si lo necesitas.

⸻

### 💸 Notas sobre costes (Twilio)

A grandes rasgos, por cada llamada:
  - Se cobra voz por minuto (precio depende del país de destino, ej. Colombia móvil ~0,0312 USD/min).
  - El Speech Recognition (cuando usas input="speech") tiene un coste adicional por uso de <Gather> (~0,018 USD por uso en el modelo por defecto).
  - El TTS (<Say>) tiene un coste muy pequeño por caracteres (~0,0008 USD / 100 caracteres en voz estándar).

En modo Trial, además:
  - Twilio añade un mensaje en inglés al inicio de la llamada (“This call is from a Twilio trial account…”) 
  - Despues de escucharlo oprimir cualquier tecla para ejecutar el mensaje personalizado.
  - Para eliminarlo, debes upgradear la cuenta.

⸻
