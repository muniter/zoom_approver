# Zoom Approver

Esta aplicación trabaja sobre una reunión de Zoom que requiere registro, y estos registros deben ser validados manualmente. Se utiliza para asegurar que las personas que son invitadas a participar a la reunión sean las autorizadas. Esto utilizando una pregunta al momento de inscribirse, que pregunta respecto a un código único que se les envío con anterioridad a los que quieren inscribirse.

Esta aplicación recibe un webhook de parte de Zoom en el que le informa cada creación de registro, y el programa compara el código único que entrego la persona al inscribirse con la base de datos (en este caso google sheets). Si ese código se encuentra en la base de datos y no ha sido usado para inscribirse antes. Entonces el programa utiliza el api de Zoom para validar el registro. Si ya el código fue utilizado deja el registro en estado pendiente para revisión manual.

## Tecnología

1. Python3: Lenguaje de programación usado
1. Flask (Web Server): recibe los Webhook
1. Requests (Paquete): Realiza el request de aprobación del registro.
1. JWT (Paquete): JSON Web Tokens para autenticación con el api de Zoom
1. Gspread (Paquete): Para interación con Google Sheet, en este caso la base de datos.
1. Docker: Para hacer el deployment
1. Google Sheet como base de datos

## Requisitos

1. Crear una JWT app en Zoom.
    1. Obtener api key, api secret de la App
    1. Inscribir url de Eventos
1. Crear un proyecto en Google Developer Console
    1. Activar API de Google Drive
    1. Activar API de Google Sheets
    1. Crear una Service Account
    1. Descargar las credenciales del Service Account.
    1. Compartir el Sheet al Service Account
1. Configurar un Reverse Proxy con SSL para recibir los eventos.
1. Llenar el archivo de Configuración

## Instrucciones

1. Configurar `config/config.json.example' y renombrar a `config/config.json`
1. Agregar las credenciales JSON de Google Service Account en un archivo con nombre `config/service-account.json`
1. Usar el contenedor:

```bash
$ cd zoom_approver
$ docker image build -t zoom_approver/zoom_approver:v1 .
$ docker run --name zoom_approver --volume $(pwd)/config:/usr/src/app/config -p 5000:5000 zoom_app
rover/zoom_approver:v1
```

Ejemplo de Docker Compose TODO

```yaml

```
