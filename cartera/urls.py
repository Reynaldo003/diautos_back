# cartera/urls.py
from rest_framework.routers import DefaultRouter

from .views import CarteraClienteViewSet

router = DefaultRouter()
router.register(
    r"clientes",
    CarteraClienteViewSet,
    basename="cartera-clientes",
)

urlpatterns = router.urls