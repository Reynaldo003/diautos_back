from django.conf import settings
from rest_framework import serializers

from .models import Rol, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id_usuario",
            "nombre",
            "apellidos",
            "usuario",
            "correo",
            "agencia",
            "telefono",
            "rol",
            "rol_nombre",
        ]


class RegistroUsuarioSerializer(serializers.Serializer):
    nombreCompleto = serializers.CharField(max_length=120)
    usuario = serializers.CharField(max_length=10)
    correo = serializers.EmailField(max_length=255)
    agencia = serializers.CharField(max_length=100)
    # ✅ CAMBIO 1: 'contrasena' → 'password'
    password = serializers.CharField(write_only=True, min_length=6)
    # ✅ CAMBIO 2: 'confirmarContrasena' → 'confirmarPassword'
    confirmarPassword = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_usuario(self, value):
        value = value.strip()
        if Usuario.objects.filter(usuario__iexact=value).exists():
            raise serializers.ValidationError("Ese usuario ya existe.")
        return value

    def validate_correo(self, value):
        value = value.strip().lower()
        if Usuario.objects.filter(correo__iexact=value).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value

    def validate(self, data):
        # ✅ CAMBIO 3: 'confirmarContrasena' → 'confirmarPassword'
        confirmar = data.get("confirmarPassword")
        if confirmar and data["password"] != confirmar:
            raise serializers.ValidationError({
                "confirmarPassword": "Las contraseñas no coinciden."
            })
        return data

    def create(self, validated_data):
        nombre_completo = validated_data["nombreCompleto"].strip()
        partes_nombre = nombre_completo.split(" ", 1)

        nombre = partes_nombre[0]
        apellidos = partes_nombre[1] if len(partes_nombre) > 1 else ""

        rol_default_id = getattr(settings, "ROL_DEFAULT_ID", None)
        if rol_default_id:
            rol = Rol.objects.filter(id_rol=rol_default_id).first()
        else:
            rol = Rol.objects.order_by("id_rol").first()

        if not rol:
            raise serializers.ValidationError(
                "No existe ningún rol registrado. Primero crea un registro en la tabla roles."
            )

        # ✅ CAMBIO 4: 'contrasena' → 'password'
        return Usuario.objects.create_user(
            usuario=validated_data["usuario"],
            correo=validated_data["correo"],
            nombre=nombre[:50],
            password=validated_data["password"],  # ← cambiado
            apellidos=apellidos[:70],
            agencia=validated_data["agencia"],
            rol=rol,
        )


class UsuarioListSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id_usuario",
            "nombre",
            "apellidos",
            "usuario",
            "correo",
            "agencia",
            "rol_nombre",
        ]