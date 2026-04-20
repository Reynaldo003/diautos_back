from rest_framework import serializers

from .models import DetalleVentasPostVentaLimpia, OrdenServicioVentaDiautos


class OrdenServicioVentaDiautosSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenServicioVentaDiautos
        fields = [
            "id",
            "nombre_cte",
            "telefono",
            "celular",
            "email",
            "marca_vehiculo",
            "version",
            "ano_modelo",
            "numero_serie",
            "importe_factura",
            "importe_costo_base",
            "importe_iva",
            "importe_isan",
            "importe_bonificacion",
            "tipo_movimiento",
            "vendedor",
            "fecha_venta",
            "folio_factura",
            "condicion_pago",
            "fecha_os",
            "id_os",
            "tipo_orden_servicio",
            "asesor",
            "transaccion",
            "clasificacion",
            "estado_os",
            "descripcion_os",
            "costo_os",
            "condicion_vehiculo",
            "estado_cliente",
            "dias_os_a_actual",
            "prioridad_prospeccion",
            "franja_retencion",
            "meses_actual_a_venta",
            "kilometraje",
        ]
        read_only_fields = ["id"]

    def validate_ano_modelo(self, value):
        if value is not None and (value < 1900 or value > 2100):
            raise serializers.ValidationError(
                "El año del modelo debe estar entre 1900 y 2100."
            )
        return value


class DetalleVentasPostVentaLimpiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVentasPostVentaLimpia
        fields = "__all__"