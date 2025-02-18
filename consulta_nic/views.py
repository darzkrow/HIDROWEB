from django.core.cache import cache
from django.shortcuts import render
from django.http import HttpResponseServerError
import requests
from django.conf import settings
import re  # Importamos el módulo de expresiones regulares


from django.views.decorators.csrf import csrf_protect



def index(request):
    hidrologicas = {
        'Hidrocaribe': 1,
        'Hidrolago': 2,
        'Hidrocapital': 3,
        'Hidrocentro': 4,
        'Hidrosuroeste': 5,
        'Hidrollanos': 6,
        'Hidroandes': 7,
        'Hidrofalcón': 8,
        'Hidropáez': 9,
        'Hidroamazonas': 10,
        'Aguas de Monagas': 11,
        'Aguas de Yaracuy': 12,
        'Hidrobolivar': 13,
        'Aguas de Mérida': 14,
        'Hidrosportuguesa': 15,
        'Hidrolara': 16,
    }

    return render(request, 'consulta_nic/index.html', {
        'hidrologicas': hidrologicas,
        'RECAPTCHA_PUBLIC_KEY': settings.RECAPTCHA_PUBLIC_KEY,
    })


@csrf_protect
def consultar_api(request):
    if request.method == 'POST':
        # Validar reCAPTCHA (si lo estás usando)
        recaptcha_response = request.POST.get('g-recaptcha-response')
        if not recaptcha_response:
            return render(request, 'consulta_nic/error.html', {'mensaje_error': 'Por favor, completa el CAPTCHA.'})

        # Verificar reCAPTCHA con Google (si lo estás usando)
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response,
        }
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()

        if not result.get('success'):
            return render(request, 'consulta_nic/error.html', {'mensaje_error': 'CAPTCHA no válido. Inténtalo de nuevo.'})

        # Si el CAPTCHA es válido, continuar con la consulta
        hidrologica_id = int(request.POST.get('HIDROLOGICA'))
        contrato = request.POST.get('CONTRATO')

        # Validar el campo CONTRATO
        if len(contrato) < 7:
            return render(request, 'consulta_nic/error.html', {'mensaje_error': 'El contrato debe tener al menos 7 caracteres.'})

        if not re.match(r'^\d+$', contrato):  # Verificar que solo contenga números
            return render(request, 'consulta_nic/error.html', {'mensaje_error': 'El contrato solo debe contener números.'})

        # Crear una clave única para la caché basada en la hidrológica y el contrato
        cache_key = f"consulta_{hidrologica_id}_{contrato}"

        # Verificar si la respuesta ya está en la caché
        cached_response = cache.get(cache_key)
        if cached_response:
            return render(request, 'consulta_nic/resultado.html', {'datos': cached_response})

        # Obtener el nombre de la hidrológica seleccionada
        hidrologicas = {
            1: 'Hidrocaribe',
            2: 'Hidrolago',
            3: 'Hidrocapital',
            4: 'Hidrocentro',
            5: 'Hidrosuroeste',
            6: 'Hidrollanos',
            7: 'Hidroandes',
            8: 'Hidrofalcón',
            9: 'Hidropáez',
            10: 'Hidroamazonas',
            11: 'Aguas de Monagas',
            12: 'Aguas de Yaracuy',
            13: 'Hidrobolivar',
            14: 'Aguas de Mérida',
            15: 'Hidrosportuguesa',
            16: 'Hidrolara',
        }
        hidrologica_nombre = hidrologicas.get(hidrologica_id, 'Desconocida')

        # Datos para la solicitud a la API
        data = {
            'HIDROLOGICA': hidrologica_id,
            'OPERACION': 1,
            'CONTRATO': contrato,
            'CANAL': 'I',
            'BANCO': '0102',
            'CAJERO': '1234',
            'BCID': '050402',
        }

        try:
            # Realizar la solicitud a la API
            url = settings.URL_ENDPOINT_HIDROVEN
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()  # Lanza una excepción si la respuesta no es exitosa

            # Obtener la respuesta JSON
            resultado = response.json()

            # Verificar si hay un código de error en el JSON
            if 'CODIGO_ERROR' in resultado:
                CODIGO_ERROR = resultado['CODIGO_ERROR']
                if CODIGO_ERROR == 0:
                    # Si no hay error, extraer solo los datos necesarios
                    datos_filtrados = {
                        'HIDROLOGICA': hidrologica_nombre,  # Usar el nombre en lugar del ID
                        'CONTRATO': contrato,
                        'IMPTOTAL': resultado.get('IMPTOTAL', 'No disponible')  # Campo IMPTOTAL del JSON
                    }
                    # Almacenar la respuesta en la caché por 20 minutos
                    cache.set(cache_key, datos_filtrados, settings.CACHE_TTL)
                    return render(request, 'consulta_nic/resultado.html', {'datos': datos_filtrados})
                elif CODIGO_ERROR == 1:
                    return render(request, 'consulta_nic/error.html', {'mensaje_error': 'Error desconocido.'})
                elif CODIGO_ERROR == 14:
                    return render(request, 'consulta_nic/error.html', {'mensaje_error': '¡Contrato Incorrecto!.'})
                elif CODIGO_ERROR == 56:
                    return render(request, 'consulta_nic/error.html', {'mensaje_error': 'La hidrológica está inactiva'})
                else:
                    return HttpResponseServerError('Error interno del servidor.')
            else:
                # Si no hay campo 'CODIGO_ERROR', asumimos que no hay errores
                datos_filtrados = {
                    'HIDROLOGICA': hidrologica_nombre,
                    'CONTRATO': contrato,
                    'IMPTOTAL': resultado.get('IMPTOTAL', 'No disponible')
                }
                # Almacenar la respuesta en la caché por 20 minutos
                cache.set(cache_key, datos_filtrados, settings.CACHE_TTL)
                return render(request, 'consulta_nic/resultado.html', {'datos': datos_filtrados})

        except requests.exceptions.RequestException as e:
            print(f"Error al conectar con la API: {str(e)}")
            mensaje_error = f"Error al conectar con la API: {str(e)}"
            return render(request, 'consulta_nic/error.html', {'mensaje_error': mensaje_error})

    return render(request, 'consulta_nic/index.html')



