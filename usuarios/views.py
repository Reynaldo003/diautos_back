# usuarios/views.py
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import (
    crear_token_usuario,
    obtener_usuario_desde_request,
    validar_contrasena_usuario,
)
from .models import Usuario
from .serializers import RegistroUsuarioSerializer, UsuarioSerializer


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        usuario_o_correo = str(request.data.get("usuario", "")).strip()
        contrasena = str(request.data.get("contrasena", ""))

        if not usuario_o_correo or not contrasena:
            return Response(
                {"detail": "Usuario y contraseña son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = (
            Usuario.objects.select_related("rol")
            .filter(
                Q(usuario__iexact=usuario_o_correo)
                | Q(correo__iexact=usuario_o_correo)
            )
            .first()
        )

        if not usuario:
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not validar_contrasena_usuario(usuario, contrasena):
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token = crear_token_usuario(usuario)

        return Response({
            "token": token,
            "usuario": UsuarioSerializer(usuario).data,
        })


class RegistroUsuarioView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegistroUsuarioSerializer(data=request.data)

        if serializer.is_valid():
            usuario = serializer.save()

            return Response(
                {
                    "detail": "Usuario creado correctamente.",
                    "usuario": UsuarioSerializer(usuario).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsuarioActualView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        usuario = obtener_usuario_desde_request(request)

        if not usuario:
            return Response(
                {"detail": "Sesión inválida o expirada."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({
            "usuario": UsuarioSerializer(usuario).data,
        })