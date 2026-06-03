# citas/urls.py
from rest_framework.routers import DefaultRouter

from .views import CitasViewSet

router = DefaultRouter()
router.register(
    r"citas",
    CitasViewSet,
    basename="citas",
)

urlpatterns = router.urls