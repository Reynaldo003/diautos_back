# clientes/serializers.py
from rest_framework import serializers
from .models import ClienteComercial, normaliza_tel_mx


class ClienteComercialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteComercial
        fields = "__all__"


def obtener_o_crear_cliente(*, nombre, telefono, correo) -> ClienteComercial:
    telefono = normaliza_tel_mx(telefono)
    if not telefono:
        raise serializers.ValidationError(
            {"telefono": "El teléfono es requerido y debe ser válido."}
        )

    cliente, _ = ClienteComercial.objects.get_or_create(
        telefono=telefono,
        defaults={
            "nombre": (nombre or "").strip(),
            "correo": (correo or "").strip(),
        },
    )

    cambios = False

    if nombre is not None and nombre.strip() and (cliente.nombre or "").strip() != nombre.strip():
        cliente.nombre = nombre.strip()
        cambios = True

    if correo is not None and (cliente.correo or "").strip() != (correo or "").strip():
        cliente.correo = (correo or "").strip()
        cambios = True

    if cambios:
        cliente.save(update_fields=["nombre", "correo", "actualizado_en"])

    return cliente


class BaseConClienteInputMixin(serializers.ModelSerializer):
    nombre = serializers.CharField(write_only=True, required=False, allow_blank=True)
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True)
    correo = serializers.CharField(write_only=True, required=False, allow_blank=True)

    cliente = ClienteComercialSerializer(read_only=True)

    cliente_id = serializers.PrimaryKeyRelatedField(
        source="cliente",
        queryset=ClienteComercial.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    def _resolver_cliente(self, validated_data):
        cliente = validated_data.get("cliente")
        if cliente:
            return cliente

        nombre = validated_data.pop("nombre", "")
        telefono = validated_data.pop("telefono", "")
        correo = validated_data.pop("correo", "")

        telefono = (telefono or "").strip()
        if not telefono:
            raise serializers.ValidationError({
                "cliente_id": "Envía cliente_id o envía al menos teléfono para crear/unir el cliente."
            })

        return obtener_o_crear_cliente(
            nombre=nombre,
            telefono=telefono,
            correo=correo,
        )

    def create(self, validated_data):
        validated_data["cliente"] = self._resolver_cliente(validated_data)
        validated_data.pop("nombre", None)
        validated_data.pop("telefono", None)
        validated_data.pop("correo", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        nombre = validated_data.pop("nombre", None)
        telefono = validated_data.pop("telefono", None)
        correo = validated_data.pop("correo", None)

        if nombre is not None or correo is not None:
            cliente = instance.cliente
            cambios = False

            if nombre is not None and nombre.strip():
                cliente.nombre = nombre.strip()
                cambios = True

            if correo is not None:
                cliente.correo = (correo or "").strip()
                cambios = True

            if cambios:
                cliente.save(update_fields=["nombre", "correo", "actualizado_en"])

        if "cliente" in validated_data:
            instance.cliente = validated_data["cliente"]

        return super().update(instance, validated_data)