from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("crear_cuenta/", views.registrar_cliente, name="crear_cuenta"),
    path("login/", views.login_cliente, name="login"),
    path("logout/", views.logout_cliente, name="logout"),
    path("activar/<str:token>/", views.activar_cuenta, name="activar_cuenta"),


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

    # 🚀 Panel de administración para el dueño de la tienda
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("gestionar-productos/", views.gestionar_productos, name="gestionar_productos"),  # Gestionar productos
    path("ver-estadisticas/", views.ver_estadisticas, name="ver_estadisticas"),  # Ver estadísticas
    path("configuracion-tienda/", views.configuracion_tienda, name="configuracion_tienda"),  # Configuración de la tienda
    path("admin/reservas/<int:pk>/", views.admin_reserva_detalle, name="admin_reserva_detalle"),

]
