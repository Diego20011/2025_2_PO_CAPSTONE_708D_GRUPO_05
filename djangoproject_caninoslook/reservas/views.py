from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import Cliente


def registrar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Cuenta creada con éxito! ✅")
            form = ClienteForm()
        else:
            if form.errors.get('email_cli'):
                messages.error(request, form.errors['email_cli'][0])
            elif form.errors.get('numero_cli'):
                messages.error(request, form.errors['numero_cli'][0])
                return redirect("login")

    else:
        form = ClienteForm()

    return render(request, "reservas/registro.html", {"form": form})


def home(request):
    return render(request, "reservas/home.html")


def login_cliente(request):
    if request.method == "POST":
        ident = (request.POST.get("user_or_email") or request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

        try:
            cli = Cliente.objects.get(email_cli__iexact=ident)
        except Cliente.DoesNotExist:
            messages.error(request, "Correo no registrado.")
            return render(request, "reservas/login.html")

        if check_password(password, cli.password):
            request.session["cliente_id"] = cli.pk            # <-- aquí
            request.session["cliente_nombre"] = cli.nombres_cli
            messages.success(request, f"Bienvenido, {cli.nombres_cli}!")
            return redirect("home")
        else:
            messages.error(request, "Contraseña incorrecta.")

    return render(request, "reservas/login.html")