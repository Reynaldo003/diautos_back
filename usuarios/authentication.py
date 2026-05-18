# usuarios/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .auth import obtener_usuario_desde_token


class SignedUserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        authorization = request.headers.get("Authorization", "")

        if not authorization.startswith("Bearer "):
            return None

        token = authorization.replace("Bearer ", "").strip()

        if not token:
            return None

        usuario = obtener_usuario_desde_token(token)

        if not usuario:
            raise AuthenticationFailed("Token inválido o expirado.")

        return (usuario, token)