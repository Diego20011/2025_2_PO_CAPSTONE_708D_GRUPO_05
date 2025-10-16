from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("crear_cuenta/", views.registrar_cliente, name="registro"),
    path("login/", views.login_cliente, name="login"),
    path("logout/", views.logout_cliente, name="logout"),

    # Navegación principal
    path("home/", views.home, name="home"),

    # Registro y reservas
    path("registrar_perro/", views.registrar_canino, name="reg_canino"),
    path("reservar_hora/", views.reserva, name="reserva"),
    path("ver_reservas/", views.ver_reservas, name="ver_reservas"),
]
