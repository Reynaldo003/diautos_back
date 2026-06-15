from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import ClienteComercial
from .serializers import ClienteComercialSerializer


from citas.models import Cita
from citas.serializers import CitaSerializer
from crm_diautos.models import RegistroPiso, PruebaManejo, Entregas
from crm_diautos.serializers import (
    RegistroPisoSerializer,
    PruebaManejoSerializer,
    EntregasSerializer,
)


class ClientesPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ClienteComercialViewSet(ModelViewSet):
    serializer_class = ClienteComercialSerializer
    pagination_class = ClientesPagination

    def get_queryset(self):
        queryset = ClienteComercial.objects.order_by("-id_cliente")

        q = self.request.query_params.get("q", "").strip()
        if q:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(nombre__icontains=q)
                | Q(telefono__icontains=q)
                | Q(correo__icontains=q)
            )

        return queryset

    @action(detail=True, methods=["get"])
    def agenda(self, request, pk=None):
        cliente = self.get_object()

        # Las 4 queries son inevitables (son 4 tablas distintas),
        # pero usamos only() para no jalar columnas pesadas innecesarias
        citas = (
            Cita.objects.filter(cliente=cliente)
            .only("id", "fecha_hora_cita", "agencia", "auto_interes", "asistencia")
            .order_by("fecha_hora_cita", "id")
        )
        piso = (
            RegistroPiso.objects.filter(cliente=cliente)
            .only("id", "fecha_hora_cita", "agencia", "auto_interes", "asistencia")
            .order_by("fecha_hora_cita", "id")
        )
        pruebas = (
            PruebaManejo.objects.filter(cliente=cliente)
            .only("id", "fecha_hora_cita", "agencia", "auto_interes", "asistencia")
            .order_by("fecha_hora_cita", "id")
        )
        entregas = (
            Entregas.objects.filter(cliente=cliente)
            .only("id", "fecha_hora_entrega", "agencia", "modelo_version", "entrega_reportada")
            .order_by("fecha_hora_entrega", "id")
        )

        data = []

        for x in citas:
            data.append({
                "tipo": "CITA",
                "id": x.id,
                "fecha_hora": x.fecha_hora_cita,
                "agencia": x.agencia,
                "auto_interes": x.auto_interes,
                "asistencia": x.asistencia,
                "detalle": CitaSerializer(x, context={"request": request}).data,
            })

        for x in piso:
            data.append({
                "tipo": "REGISTRO_PISO",
                "id": x.id,
                "fecha_hora": x.fecha_hora_cita,
                "agencia": x.agencia,
                "auto_interes": x.auto_interes,
                "asistencia": x.asistencia,
                "detalle": RegistroPisoSerializer(x, context={"request": request}).data,
            })

        for x in pruebas:
            data.append({
                "tipo": "PRUEBA_MANEJO",
                "id": x.id,
                "fecha_hora": x.fecha_hora_cita,
                "agencia": x.agencia,
                "auto_interes": x.auto_interes,
                "asistencia": x.asistencia,
                "detalle": PruebaManejoSerializer(x, context={"request": request}).data,
            })

        for x in entregas:
            data.append({
                "tipo": "ENTREGA",
                "id": x.id,
                "fecha_hora": x.fecha_hora_entrega,
                "agencia": x.agencia,
                "modelo_version": x.modelo_version,
                "entrega_reportada": x.entrega_reportada,
                "detalle": EntregasSerializer(x, context={"request": request}).data,
            })

        data.sort(key=lambda r: (r["fecha_hora"] is None, r["fecha_hora"], r["id"]))
        return Response(data)