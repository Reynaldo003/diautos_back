from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import (
    crear_token_usuario,
    obtener_usuario_desde_request,
    validar_contrasena_usuario,
)
from .models import Usuario
from .serializers import RegistroUsuarioSerializer, UsuarioListSerializer, UsuarioSerializer


class UsuariosPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        usuario_o_correo = str(request.data.get("usuario", "")).strip()
        # ✅ CAMBIO: aceptar tanto 'contrasena' como 'password' (compatibilidad)
        contrasena = str(request.data.get("password") or request.data.get("contrasena", ""))

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

        if not usuario or not validar_contrasena_usuario(usuario, contrasena):
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
        # ✅ CAMBIO: convertir 'password' a 'contrasena' para compatibilidad con el serializer
        data = request.data.copy()
        if 'password' in data and 'contrasena' not in data:
            data['contrasena'] = data['password']
        if 'confirmarPassword' in data and 'confirmarContrasena' not in data:
            data['confirmarContrasena'] = data['confirmarPassword']
        
        serializer = RegistroUsuarioSerializer(data=data)

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


class UsuarioListView(APIView):
    """Lista de usuarios con paginación y filtro opcional."""

    def get(self, request):
        queryset = (
            Usuario.objects.select_related("rol")
            .only(
                "id_usuario", "nombre", "apellidos",
                "usuario", "correo", "agencia",
                "rol__nombre",
            )
            .filter(is_active=True)
            .order_by("nombre", "apellidos")
        )

        # Filtro opcional por nombre, usuario, agencia o rol
        q = request.query_params.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q)
                | Q(apellidos__icontains=q)
                | Q(usuario__icontains=q)
                | Q(agencia__icontains=q)
            )

        agencia = request.query_params.get("agencia", "").strip()
        if agencia:
            queryset = queryset.filter(agencia__iexact=agencia)

        paginator = UsuariosPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = UsuarioListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


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