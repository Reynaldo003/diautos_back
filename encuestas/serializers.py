# encuestas/serializers.py
from rest_framework import serializers
from .models import EncuestaServicio

class EncuestaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncuestaServicio
        fields = [
            "id_encuesta",
            "creado",
            "numero_OS",
            "asesor",
            "satisfaccion_agendar_cita",
            "satisfaccion_exp_area_servicio",
            "mostraron_inventario_inicial_vehiculo",
            "explicacion_clara_trabajo_realizado",
            "invitacion_realizar_inventario",
            "entrego_reporte_multipuntos",
            "trabajo_realizado_cumple_espectativa",
            "comentario",
        ]
        read_only_fields = ["id_encuesta", "creado"]

    def validate(self, attrs):
        campos_calificacion = [
            "satisfaccion_agendar_cita",
            "satisfaccion_exp_area_servicio",
        ]

        for campo in campos_calificacion:
            valor = attrs.get(campo)

            if valor in [None, ""]:
                raise serializers.ValidationError({
                    campo: "Este campo es obligatorio."
                })

            try:
                valor_entero = int(valor)
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    campo: "Debe ser un número entre 1 y 5."
                })

            if valor_entero < 1 or valor_entero > 5:
                raise serializers.ValidationError({
                    campo: "Debe ser un valor entre 1 y 5."
                })

            attrs[campo] = valor_entero

        attrs["numero_OS"] = (attrs.get("numero_OS") or "").strip()
        attrs["asesor"] = (attrs.get("asesor") or "").strip()
        attrs["comentario"] = (attrs.get("comentario") or "").strip()

        if not attrs["numero_OS"]:
            raise serializers.ValidationError({
                "numero_OS": "Este campo es obligatorio."
            })

        return attrs