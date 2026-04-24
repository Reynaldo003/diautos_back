# usuarios/auth.py
from django.core import signing
from django.contrib.auth.hashers import check_password, identify_hasher, make_password

from .models import Usuario


TOKEN_SALT = "crm_chevrolet.auth"
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 días


def crear_token_usuario(usuario):
    return signing.dumps(
        {"id_usuario": usuario.id_usuario},
        salt=TOKEN_SALT,
    )


def obtener_usuario_desde_token(token):
    try:
        data = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE,
        )

        return Usuario.objects.select_related("rol").get(
            id_usuario=data.get("id_usuario")
        )

    except Exception:
        return None


def obtener_usuario_desde_request(request):
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()

    if not token:
        return None

    return obtener_usuario_desde_token(token)


def es_password_hasheado(valor):
    try:
        identify_hasher(valor)
        return True
    except Exception:
        return False


def validar_contrasena_usuario(usuario, contrasena_plana):
    """
    Valida la contraseña.

    Soporta dos casos:
    1. Contraseñas ya hasheadas con Django.
    2. Contraseñas antiguas guardadas en texto plano.

    Si detecta una contraseña vieja en texto plano y coincide,
    la actualiza automáticamente a hash seguro.
    """

    contrasena_guardada = usuario.contrasena or ""

    if es_password_hasheado(contrasena_guardada):
        return check_password(contrasena_plana, contrasena_guardada)

    es_valida = contrasena_guardada == contrasena_plana

    if es_valida:
        usuario.contrasena = make_password(contrasena_plana)
        usuario.save(update_fields=["contrasena"])

    return es_valida