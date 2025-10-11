from django.urls import path

from . import views

urlpatterns = [
    path("crear_cuenta", views.registrar_cliente, name="registro"),
    path("login/", views.login_cliente, name="login"),
    path("home", views.home, name="home"),
    path("reservar_hora", views.reserva, name="reserva"),
    ]