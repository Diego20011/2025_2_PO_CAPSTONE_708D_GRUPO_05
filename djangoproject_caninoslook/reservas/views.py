from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.contrib import messages

# Create your views here.
def registrar_cliente(request):
    cuentaCreada=False
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            cuentaCreada=True
    else:
        form = ClienteForm()

    return render(request, "reservas/registro.html", {"form": form, "cuentaCreada": cuentaCreada})