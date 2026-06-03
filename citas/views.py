# citas/views.py
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from usuarios.authentication import SignedUserAuthentication

from .models import Cita
from .serializers import CitaSerializer


class CitasViewSet(ModelViewSet):
    authentication_classes = [SignedUserAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CitaSerializer

    def get_queryset(self):
        queryset = (
            Cita.objects.select_related("cliente")
            .all()
            .order_by("-id")
        )

        q = str(self.request.query_params.get("q", "")).strip()
        asistencia = str(self.request.query_params.get("asistencia", "")).strip()
        agencia = str(self.request.query_params.get("agencia", "")).strip()
        tipo_cita = str(self.request.query_params.get("tipo_cita", "")).strip()
        fecha_desde = str(self.request.query_params.get("fecha_desde", "")).strip()
        fecha_hasta = str(self.request.query_params.get("fecha_hasta", "")).strip()

        if q:
            queryset = queryset.filter(
                Q(cliente__nombre__icontains=q)
                | Q(cliente__telefono__icontains=q)
                | Q(cliente__correo__icontains=q)
                | Q(agencia__icontains=q)
                | Q(auto_interes__icontains=q)
                | Q(tipo_cita__icontains=q)
                | Q(fuente_prospeccion__icontains=q)
                | Q(asesor_digital__icontains=q)
                | Q(asesor_piso__icontains=q)
                | Q(comentarios__icontains=q)
            )

        if asistencia in {"true", "false"}:
            queryset = queryset.filter(asistencia=asistencia == "true")

        if agencia:
            queryset = queryset.filter(agencia__icontains=agencia)

        if tipo_cita:
            queryset = queryset.filter(tipo_cita__icontains=tipo_cita)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora_cita__date__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora_cita__date__lte=fecha_hasta)

        return queryset