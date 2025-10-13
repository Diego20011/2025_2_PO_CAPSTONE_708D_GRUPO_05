from django.urls import path

from . import views

urlpatterns = [
    path("crear_cuenta", views.registrar_cliente, name="registro"),
    path("login/", views.login_cliente, name="login"),
    path("home", views.home, name="home"),
    path("reservar_hora", views.reserva, name="reserva"),
    path("registrar_perro", views.registrar_canino, name="reg_canino"),
    path("ver_reservas", views.ver_reservas, name="ver_reservas"),
    ]