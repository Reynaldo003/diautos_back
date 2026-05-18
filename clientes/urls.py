# clientes/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClienteComercialViewSet,
)

router = DefaultRouter()
router.register(r"clientes-comerciales", ClienteComercialViewSet, basename="clientes-comerciales")
urlpatterns = [
    path("api/", include(router.urls)),
]