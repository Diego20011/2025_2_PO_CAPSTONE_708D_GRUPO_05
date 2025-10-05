from django.shortcuts import render
from .forms import ClienteForm
from django.contrib import messages

def registrar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Cuenta creada con éxito! ✅")
            # Crear un formulario vacío para que se vea limpio
            form = ClienteForm()
        else:
            # Revisar si el error es por email duplicado
            if form.errors.get('email_cli'):
                messages.error(request, form.errors['email_cli'][0])
            elif form.errors.get('numero_cli'):
                messages.error(request, form.errors['numero_cli'][0])
    else:
        form = ClienteForm()

    return render(request, "reservas/registro.html", {"form": form})
