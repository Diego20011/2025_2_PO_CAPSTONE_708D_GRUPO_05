from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import RegistroDeClienteForm, RegistroDeCaninoForm
from .models import Cliente, Reserva, Canino

# Registro de cliente
def registrar_cliente(request):
    form = RegistroDeClienteForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.password_cli = make_password(form.cleaned_data["password_cli"])
            cliente.save()
            messages.success(request, "¡Cuenta creada con éxito! ✅")
            return redirect("login")
    return render(request, "reservas/registro.html", {"form": form})

# Login de cliente
def login_cliente(request):
    if request.session.get("cliente_id"):
        return redirect("home")
    if request.method == "POST":
        ident = (request.POST.get("user_or_email") or "").strip()
        password = request.POST.get("password") or ""

        try:
            cli = Cliente.objects.get(email_cli__iexact=ident)
        except Cliente.DoesNotExist:
            messages.error(request, "Correo no registrado.")
            return render(request, "reservas/login.html")

        if check_password(password, cli.password_cli):
            request.session["cliente_id"] = cli.pk
            request.session["cliente_nombre"] = cli.nombres_cli
            messages.success(request, f"Bienvenido, {cli.nombres_cli}!")
            return redirect("home")
        else:
            messages.error(request, "Contraseña incorrecta.")
    return render(request, "reservas/login.html")

# Registro de canino
def registrar_canino(request):
    form = RegistroDeCaninoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        canino = form.save(commit=False)
        canino.cliente_id_can_id = request.session.get('cliente_id')
        canino.save()
        messages.success(request, "Mascota registrada correctamente.")
        return redirect("reservar_hora")
    return render(request, "reservas/reg_perro.html", {"form": form})

# Home
def home(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        return render(request, "reservas/home_no_registrado.html")

    reservas = Reserva.objects.filter(
        cliente_id_res=cliente_id,
        fecha_res__gte=timezone.localdate()
    ).order_by("fecha_res")

    return render(request, "reservas/home.html", {
        "reservas": reservas,
    })

# Reserva de hora

#FALTA CORREGIR QUE CUANDO PONEN EL MISMO DÍA OMITA LAS HORAS QUE YA NO SE PUEDEN.
def reserva(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        return redirect("login")

    perros_cli = Canino.objects.filter(cliente_id_can_id=cliente_id)
    if not perros_cli.exists():
        messages.warning(request, "Debes registrar al menos una mascota antes de hacer una reserva.")
        return redirect("registrar_perro")

    servSelecc = request.GET.get("servicio")
    fechaDeseada = request.GET.get("fecha_reserva")
    fechaD_formateada = "-".join(reversed(fechaDeseada.split("-"))) if fechaDeseada else ""

    res_x_fecha = Reserva.objects.filter(fecha_res=fechaDeseada).order_by("hora_res")
    lista_horas_full = [f"{h:02d}:{m:02d}:00" for h in range(9, 18) for m in (0, 30)]
    horasD_baño, horasD_corte = [], []

    if res_x_fecha.exists() and servSelecc:
        i, c = 0, 0
        while i < len(lista_horas_full) and c < len(res_x_fecha):
            while lista_horas_full[i] == res_x_fecha[c].hora_res.strftime("%H:%M:%S"):
                if res_x_fecha[c].servicio_res == "Baño":
                    del lista_horas_full[i:i+2]
                elif res_x_fecha[c].servicio_res == "Corte":
                    del lista_horas_full[i:i+6]
                c += 1
                if c >= len(res_x_fecha):
                    break
            i += 1

        horasTo_baño = lista_horas_full
        horasTo_corte = lista_horas_full

        if servSelecc == "Baño":
            for q in range(len(horasTo_baño) - 1):
                if (datetime.strptime(horasTo_baño[q], "%H:%M:%S") + timedelta(minutes=30)).strftime("%H:%M:%S") == horasTo_baño[q+1]:
                    horasD_baño.append(horasTo_baño[q])

        if servSelecc == "Corte":
            for q2 in range(len(horasTo_corte) - 5):
                if all(
                    (datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(minutes=30 * i)).strftime("%H:%M:%S") == horasTo_corte[q2 + i]
                    for i in range(1, 6)
                ):
                    horasD_corte.append(horasTo_corte[q2])
    else:
        horasD_baño = lista_horas_full[:17]
        horasD_corte = lista_horas_full[:13]

    if request.GET.get("hora") and request.GET.get("perro"):
        reserva_nueva = Reserva.objects.create(
            servicio_res=servSelecc,
            hora_res=request.GET.get("hora"),
            fecha_res=fechaDeseada,
            medio_pago_res="Efectivo",
            valor_res=0,
            confirm_pago_res=0,
            cliente_id_res_id=cliente_id,
            canino_id_res_id=request.GET.get("perro"),
        )
        request.session["ultima_reserva_id"] = reserva_nueva.pk
        messages.success(request, "Reserva creada exitosamente.")
        return redirect("ver_reservas")

    return render(request, "reservas/reserva.html", {
        "res_x_fecha": res_x_fecha,
        "fechaDeseada": fechaDeseada,
        "fechaD_formateada": fechaD_formateada,
        "servSelecc": servSelecc,
        "horasD_baño": horasD_baño,
        "horasD_corte": horasD_corte,
        "perros_cli": perros_cli,
    })

# Ver reservas
# FALTA ORDENAR LAS RESERVAS POR FECHA Y HORA, TENEMOS SOLO POR HORA.
def ver_reservas(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        return redirect("login")

    ver_xfecha = request.GET.get("fecha_reserva")
    fecha = ver_xfecha or timezone.localdate()

    res_xfecha = Reserva.objects.filter(
        fecha_res=fecha,
        cliente_id_res_id=cliente_id
    ).order_by("hora_res")

    ultima_reserva = None
    reserva_id = request.session.pop("ultima_reserva_id", None)
    if reserva_id:
        try:
            ultima_reserva = Reserva.objects.get(pk=reserva_id, cliente_id_res_id=cliente_id)
        except Reserva.DoesNotExist:
            ultima_reserva = None

    return render(request, "reservas/ver_reservas.html", {
        "res_xfecha": res_xfecha,
        "ver_xfecha": ver_xfecha,
        "ultima_reserva": ultima_reserva,
    })

from django.utils import timezone

def servicios(request):
    today = timezone.localdate().strftime("%Y-%m-%d")
    return render(request, 'reservas/servicios.html', {"today": today})

# Logout
def logout_cliente(request):
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("login")
