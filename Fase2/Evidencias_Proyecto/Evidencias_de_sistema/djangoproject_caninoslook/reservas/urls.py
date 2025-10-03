from django.urls import path

from . import views

urlpatterns = [
    path("crear_cuenta", views.registrar_cliente, name="registro"),
]