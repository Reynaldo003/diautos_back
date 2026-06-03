# citas/views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Cita
from .serializers import ClienteComercialSerializer, CitaSerializer
from clientes.models import ClienteComercial

class ClienteComercialViewSet(ModelViewSet):
    queryset = ClienteComercial.objects.all().order_by("-id_cliente")
    serializer_class = ClienteComercialSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def agenda(self, request, pk=None):
        cliente = self.get_object()

        citas = Cita.objects.filter(cliente=cliente).order_by(
            "fecha_hora_cita",
            "id",
        )

        data = []

        for cita in citas:
            data.append({
                "tipo": "CITA",
                "id": cita.id,
                "fecha_hora": cita.fecha_hora_cita,
                "agencia": cita.agencia,
                "auto_interes": cita.auto_interes,
                "asistencia": cita.asistencia,
                "detalle": CitaSerializer(cita, context={"request": request}).data,
            })

        return Response(data)


class CitasViewSet(ModelViewSet):
    queryset = Cita.objects.select_related("cliente").all().order_by("-id")
    serializer_class = CitaSerializer
    permission_classes = [AllowAny]