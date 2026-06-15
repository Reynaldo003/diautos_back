# retencion/urls.py
from rest_framework.routers import DefaultRouter

from .views import OrdenServicioVentaDiautosViewSet

router = DefaultRouter()
router.register(r"ordenes-servicio-ventas", OrdenServicioVentaDiautosViewSet, basename="ordenes-servicio-ventas",)

urlpatterns = router.urls
