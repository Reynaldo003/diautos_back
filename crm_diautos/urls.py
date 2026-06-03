# crm_diautos/urls.py
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("retencion.urls")),
    path("api/auth/", include("usuarios.urls")),
    path("api/cartera/", include("cartera.urls")),
    path("encuestas/api/", include("encuestas.urls")),
    path("usados/", include("avaluos.urls")),
    path("citas/api/", include("citas.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)