#encuestas/views.py
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import EncuestaServicio
from .serializers import EncuestaServicioSerializer


class EncuestasPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class PublicEncuestaServicioCreateView(generics.CreateAPIView):

    queryset = EncuestaServicio.objects.none()
    serializer_class = EncuestaServicioSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post", "options", "head"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        encuesta = serializer.save()

        return Response(
            {
                "message": "Encuesta registrada correctamente.",
                "data": self.get_serializer(encuesta).data,
            },
            status=status.HTTP_201_CREATED,
        )


class EncuestaServicioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EncuestaServicioSerializer
    permission_classes = [AllowAny]
    pagination_class = EncuestasPagination

    def get_queryset(self):
        queryset = EncuestaServicio.objects.order_by("-creado")

        # Filtro opcional por asesor
        asesor = self.request.query_params.get("asesor", "").strip()
        if asesor:
            queryset = queryset.filter(asesor__icontains=asesor)

        # Filtro opcional por número de OS
        numero_os = self.request.query_params.get("numero_os", "").strip()
        if numero_os:
            queryset = queryset.filter(numero_OS__icontains=numero_os)

        return queryset