from django.urls import path

from .views import LoginView, RegistroUsuarioView, UsuarioActualView, UsuarioListView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("registro/", RegistroUsuarioView.as_view(), name="registro"),
    path("me/", UsuarioActualView.as_view(), name="usuario-actual"),
    

    path("lista/", UsuarioListView.as_view(), name="usuario-lista"),
]