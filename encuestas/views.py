#encuestas/views.py
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import EncuestaServicio
from .serializers import EncuestaServicioSerializer


class PublicEncuestaServicioCreateView(generics.CreateAPIView):
    queryset = EncuestaServicio.objects.all().order_by("-id_encuesta")
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
    queryset = EncuestaServicio.objects.all().order_by("-creado")