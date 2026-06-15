from rest_framework import serializers

from .models import (
    DetalleVentasPostVentaLimpia,
    OrdenServicioVentaDiautos,
    RetencionComentario,
)


class OrdenServicioVentaDiautosSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenServicioVentaDiautos
        fields = [
            "id", "nombre_cte", "telefono", "celular", "email",
            "marca_vehiculo", "version", "ano_modelo", "numero_serie",
            "importe_factura", "importe_costo_base", "importe_iva",
            "importe_isan", "importe_bonificacion", "tipo_movimiento",
            "vendedor", "fecha_venta", "folio_factura", "condicion_pago",
            "fecha_os", "id_os", "tipo_orden_servicio", "asesor",
            "transaccion", "clasificacion", "estado_os", "descripcion_os",
            "costo_os", "condicion_vehiculo", "estado_cliente",
            "dias_os_a_actual", "prioridad_prospeccion", "franja_retencion",
            "meses_actual_a_venta", "kilometraje",
        ]
        read_only_fields = ["id"]

    def validate_ano_modelo(self, value):
        if value is not None and (value < 1900 or value > 2100):
            raise serializers.ValidationError(
                "El año del modelo debe estar entre 1900 y 2100."
            )
        return value


class DetalleVentasPostVentaListSerializer(serializers.ModelSerializer):
    """Serializer ligero para la tabla/listado general de Postventa."""
    class Meta:
        model = DetalleVentasPostVentaLimpia
        fields = [
            "ore_idorden",
            "nombre_cte",
            "tel_contacto",
            "ore_fechaord",
            "ore_fechacie",
            "tiporden",
            "ore_status",
            "asesor",
            "ore_numserie",
            "ord_subtotal",
            "veh_noplacas",
            "factura",
        ]


class DetalleVentasPostVentaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo solo para el detalle de un registro."""
    class Meta:
        model = DetalleVentasPostVentaLimpia
        fields = "__all__"


class RetencionComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetencionComentario
        fields = [
            "id", "tipo", "venta", "vin", "folio_factura",
            "fecha_venta", "id_os", "comentario", "creado_por",
            "creado_en", "actualizado_en", "activo",
        ]
        read_only_fields = [
            "id", "tipo", "venta", "vin", "folio_factura",
            "fecha_venta", "id_os", "creado_por", "creado_en",
            "actualizado_en", "activo",
        ]

    def validate_comentario(self, value):
        texto = str(value or "").strip()
        if not texto:
            raise serializers.ValidationError("El comentario es obligatorio.")
        if len(texto) > 2000:
            raise serializers.ValidationError(
                "El comentario no puede superar 2000 caracteres."
            )
        return texto