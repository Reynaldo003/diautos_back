# encuestas/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PublicEncuestaServicioCreateView, EncuestaServicioViewSet


router = DefaultRouter()
router.register(
    r"encuestas-servicio",
    EncuestaServicioViewSet,
    basename="encuestas-servicio"
)

urlpatterns = [
    path(
        "public/encuestas-servicio/",
        PublicEncuestaServicioCreateView.as_view(),
        name="public-encuesta-servicio-create"
    ),
    path("", include(router.urls)),
]