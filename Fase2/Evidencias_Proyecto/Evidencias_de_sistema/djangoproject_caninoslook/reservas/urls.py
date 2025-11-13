from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("crear_cuenta/", views.registrar_cliente, name="crear_cuenta"),
    path("login/", views.login_cliente, name="login"),
    path("logout/", views.logout_cliente, name="logout"),

    # Navegación principal
    path("", views.home, name="home"),

    # Registro y reservas
    path("registrar_perro/", views.registrar_canino, name="registrar_perro"),
    path("reservar_hora/", views.reserva, name="reservar_hora"),
    path("ver_reservas/", views.ver_reservas, name="ver_reservas"),
    path("servicios/", views.servicios, name="servicios"),

    # 🐾 Gestión de mascotas
    path("mis_mascotas/", views.mis_mascotas, name="mis_mascotas"),
    path("mascotas/<int:pk>/editar/", views.editar_mascota, name="editar_mascota"),
    path("mascotas/<int:pk>/eliminar/", views.eliminar_mascota, name="eliminar_mascota"),

    # 📜 Historial de reservas
    path("historial_reservas/", views.historial_reservas, name="historial_reservas"),
]
