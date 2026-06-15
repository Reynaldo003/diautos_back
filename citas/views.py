# citas/views.py
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from usuarios.authentication import SignedUserAuthentication
from .models import Cita
from .serializers import CitaSerializer, CitaListSerializer


class CitasPagination(PageNumberPagination):
    page_size = 50                    # 50 por página, no 500 de un golpe
    page_size_query_param = "page_size"
    max_page_size = 200


class CitasViewSet(ModelViewSet):
    authentication_classes = [SignedUserAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CitasPagination

    def get_serializer_class(self):
        # Lista → serializer ligero. Detalle/crear/editar → completo
        if self.action == "list":
            return CitaListSerializer
        return CitaSerializer

    def get_queryset(self):
        # Solo los campos que necesita la lista
        queryset = (
            Cita.objects.select_related("cliente")
            .only(
                "id", "agencia", "auto_interes", "fecha_hora_cita",
                "asistencia", "tipo_cita", "fuente_prospeccion",
                "asesor_digital", "asesor_piso",
                "estado_gestion",           # ← AGREGADO (si no estaba)
                "detalle_gestion",          # ← NUEVO CAMPO
                "comentarios",              # ← si lo necesitas en lista
                # campos del cliente que usa el serializer
                "cliente__id", "cliente__nombre",
                "cliente__telefono", "cliente__correo",
            )
            .order_by("-id")
        )

        q = self.request.query_params.get("q", "").strip()
        asistencia = self.request.query_params.get("asistencia", "").strip()
        agencia = self.request.query_params.get("agencia", "").strip()
        tipo_cita = self.request.query_params.get("tipo_cita", "").strip()
        fecha_desde = self.request.query_params.get("fecha_desde", "").strip()
        fecha_hasta = self.request.query_params.get("fecha_hasta", "").strip()

        if q:
            queryset = queryset.filter(
                Q(cliente__nombre__icontains=q)
                | Q(cliente__telefono__icontains=q)
                | Q(agencia__icontains=q)
                | Q(auto_interes__icontains=q)
                | Q(tipo_cita__icontains=q)
                | Q(asesor_piso__icontains=q)
                # quitamos los menos buscados para reducir carga
            )

        if asistencia in {"true", "false"}:
            queryset = queryset.filter(asistencia=asistencia == "true")

        if agencia:
            queryset = queryset.filter(agencia__iexact=agencia)  # iexact > icontains cuando es valor exacto

        if tipo_cita:
            queryset = queryset.filter(tipo_cita__iexact=tipo_cita)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora_cita__date__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora_cita__date__lte=fecha_hasta)

        return queryset