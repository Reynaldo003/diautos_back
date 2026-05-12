# cartera/serializers.py
from rest_framework import serializers

from usuarios.models import Usuario
from .models import CarteraCliente


class UsuarioBDCSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id_usuario",
            "nombre",
            "apellidos",
            "nombre_completo",
            "usuario",
            "correo",
            "agencia",
            "telefono",
            "rol_nombre",
        ]

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellidos or ''}".strip()


class CarteraClienteSerializer(serializers.ModelSerializer):
    asesor_id = serializers.IntegerField(source="asesor_asignado.id_usuario", read_only=True)
    asesor_nombre = serializers.SerializerMethodField()
    creado_por_nombre = serializers.SerializerMethodField()
    venta_id = serializers.IntegerField(source="venta.id", read_only=True)

    class Meta:
        model = CarteraCliente
        fields = [
            "id",
            "venta_id",
            "vin",
            "nombre_cliente",
            "telefono",
            "celular",
            "email",
            "marca_vehiculo",
            "modelo",
            "version",
            "ano_modelo",
            "fecha_venta",
            "folio_factura",
            "vendedor",
            "fecha_os",
            "id_os",
            "asesor_servicio",
            "estado_cliente",
            "dias_os_a_actual",
            "meses_actual_a_venta",
            "franja_retencion",
            "prioridad_prospeccion",
            "kilometraje",
            "asesor_id",
            "asesor_nombre",
            "estado_gestion",
            "asignado_en",
            "actualizado_en",
            "creado_por_nombre",
            "origen",
            "activo",
        ]
        read_only_fields = fields

    def get_asesor_nombre(self, obj):
        asesor = obj.asesor_asignado
        return f"{asesor.nombre} {asesor.apellidos or ''}".strip()

    def get_creado_por_nombre(self, obj):
        if not obj.creado_por:
            return ""

        return f"{obj.creado_por.nombre} {obj.creado_por.apellidos or ''}".strip()


class CarteraAsignacionAutomaticaSerializer(serializers.Serializer):
    asesores_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    fecha_venta_desde = serializers.DateField(required=False)
    fecha_venta_hasta = serializers.DateField(required=False)
    simular = serializers.BooleanField(required=False, default=False)

    def validate_asesores_ids(self, value):
        ids_unicos = list(dict.fromkeys(value))

        asesores_existentes = Usuario.objects.filter(
            id_usuario__in=ids_unicos
        ).count()

        if asesores_existentes != len(ids_unicos):
            raise serializers.ValidationError(
                "Uno o más asesores seleccionados no existen."
            )

        return ids_unicos

    def validate(self, data):
        desde = data.get("fecha_venta_desde")
        hasta = data.get("fecha_venta_hasta")

        if desde and hasta and desde > hasta:
            raise serializers.ValidationError({
                "fecha_venta_hasta": "La fecha final no puede ser menor que la fecha inicial."
            })

        return data


class CarteraClienteManualSerializer(serializers.Serializer):
    nombre_cliente = serializers.CharField(max_length=255)
    vin = serializers.CharField(max_length=150)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    celular = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    marca_vehiculo = serializers.CharField(max_length=100, required=False, allow_blank=True)
    version = serializers.CharField(max_length=150, required=False, allow_blank=True)
    ano_modelo = serializers.IntegerField(required=False, allow_null=True)

    def validate_vin(self, value):
        vin = str(value or "").strip().upper()

        if not vin:
            raise serializers.ValidationError("El VIN es obligatorio.")

        if CarteraCliente.objects.filter(vin_normalizado=vin).exists():
            raise serializers.ValidationError(
                "Este VIN ya tiene un asesor asignado en cartera."
            )

        return vin