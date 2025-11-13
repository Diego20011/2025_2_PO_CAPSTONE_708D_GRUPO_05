from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from functools import wraps

from .forms import RegistroDeClienteForm, RegistroDeCaninoForm
from .models import Cliente, Reserva, Canino

# ==========================
# Constantes
# ==========================
DURACIONES = {
    'Baño': timedelta(minutes=45),
    'Corte': timedelta(hours=2),
    'Corte y baño': timedelta(hours=2, minutes=45),
    'Baño + Uñas': timedelta(hours=1),
    'Baño + Oidos': timedelta(hours=1),
    'Baño + Uñas y oidos': timedelta(hours=1),
    'Corte + Uñas': timedelta(hours=2, minutes=15),
    'Corte + Oidos': timedelta(hours=2, minutes=15),
    'Corte + Uñas y oidos': timedelta(hours=2, minutes=15),
    'Corte y baño + Uñas y oidos': timedelta(hours=3),
    'Corte y baño + Uñas': timedelta(hours=3),
    'Corte y baño + Oidos': timedelta(hours=3),
    'Uñas y oidos': timedelta(minutes=15),
    'Uñas': timedelta(minutes=15),
    'Oidos': timedelta(minutes=15),
}

PRECIOS = {
    'Pequeño': 20000,
    'Mediano': 25000,
    'Grande': 30000,
}

SERVICIOS_VALIDOS = {
    "Corte": "Corte de pelo",
    "Baño": "Baño",
    "Corte y baño": "Estética full",
    "Uñas": "Corte de uñas",
    "Oidos": "Limpieza de oídos",
    "Uñas y oidos": "Cuidados Full"
}

# ==========================
# Decorador para login
# ==========================
def requiere_login(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("cliente_id"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper

# ==========================
# Función auxiliar
# ==========================
def calcular_horas_disponibles(servicioConcat, reservas_existentes):
    lista_horas_full = [f"{h:02d}:{m:02d}:00" for h in range(9, 18) for m in (0, 15, 30, 45)]
    lista_horas_full.append("18:00:00")
    horas_disponibles = []

    if reservas_existentes.exists():
        for reserva in reservas_existentes:
            duracion = DURACIONES.get(reserva.servicio_res)
            if not duracion:
                continue
            bloque = int(duracion.total_seconds() / 900)
            try:
                idx = lista_horas_full.index(reserva.hora_res.strftime("%H:%M:%S"))
                del lista_horas_full[idx:idx + bloque]
            except ValueError:
                continue

    duracion = DURACIONES.get(servicioConcat)
    if duracion:
        bloques = int(duracion.total_seconds() / 900)
        for i in range(len(lista_horas_full) - bloques):
            inicio = datetime.strptime(lista_horas_full[i], "%H:%M:%S")
            if all((inicio + timedelta(minutes=15 * j)).strftime("%H:%M:%S") == lista_horas_full[i + j] for j in range(1, bloques)):
                horas_disponibles.append(lista_horas_full[i])

    return horas_disponibles or lista_horas_full

# ==========================
# Vistas
# ==========================

def registrar_cliente(request):
    form = RegistroDeClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cliente = form.save(commit=False)
        cliente.password_cli = make_password(form.cleaned_data["password_cli"])
        cliente.save()
        messages.success(request, "¡Cuenta creada con éxito! ✅")
        return redirect("login")
    return render(request, "reservas/registro.html", {"form": form})

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
            messages.success(request, f"Bienvenido, {cli.nombres_cli}! 👋")
            return redirect("home")
        else:
            messages.error(request, "Contraseña incorrecta.")
    return render(request, "reservas/login.html")

@requiere_login
def registrar_canino(request):
    cliente_id = request.session["cliente_id"]
    editar_id = request.GET.get("editar")
    canino = None

    if editar_id:
        canino = get_object_or_404(Canino, pk=editar_id, cliente_id_can_id=cliente_id)

    form = RegistroDeCaninoForm(request.POST or None, instance=canino)
    if request.method == "POST" and form.is_valid():
        nuevo_canino = form.save(commit=False)
        nuevo_canino.cliente_id_can_id = cliente_id
        nuevo_canino.save()
        messages.success(request, "Mascota guardada correctamente ✅")
        return redirect("home")

    return render(request, "reservas/reg_perro.html", {"form": form, "canino": canino})

@requiere_login
def eliminar_mascota(request, pk):
    cliente_id = request.session["cliente_id"]
    canino = get_object_or_404(Canino, pk=pk, cliente_id_can_id=cliente_id)
    tiene_reservas_futuras = Reserva.objects.filter(
        canino_id_res_id=canino.pk,
        fecha_res__gte=timezone.localdate()
    ).exists()

    if request.method == "POST":
        if tiene_reservas_futuras:
            messages.error(request, "No puedes eliminar esta mascota: tiene reservas futuras.")
        else:
            canino.delete()
            messages.success(request, "Mascota eliminada correctamente ✅")
        return redirect("home")

    return render(request, "reservas/eliminar_mascota.html", {
        "canino": canino,
        "tiene_reservas_futuras": tiene_reservas_futuras
    })

def home(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        return render(request, "reservas/home_no_registrado.html")

    reservas = Reserva.objects.filter(
        cliente_id_res=cliente_id,
        fecha_res__gte=timezone.localdate()
    ).order_by("fecha_res")

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    reserva_id = request.session.pop("ultima_reserva_id", None)
    ultima_reserva = Reserva.objects.filter(pk=reserva_id, cliente_id_res_id=cliente_id).first() if reserva_id else None
    mascotas = Canino.objects.filter(cliente_id_can_id=cliente_id).order_by("nombre_can")


    return render(request, "reservas/home.html", {
        "reservas": reservas,
        "cliente": cliente,
        "mascotas": mascotas,
        "ultima_reserva": ultima_reserva,
    })


@requiere_login
def reserva(request):
    cliente_id = request.session["cliente_id"]
    perros_cli = Canino.objects.filter(cliente_id_can_id=cliente_id)
    if not perros_cli.exists():
        messages.warning(request, "Debes registrar al menos una mascota antes de hacer una reserva.")
        return redirect("registrar_perro")

    servSelecc = request.GET.get("servicio")
    servSelecc2 = request.GET.get("servicio2")
    fechaDeseada = request.GET.get("fecha_reserva")

    servicioConcat = " + ".join(filter(None, [servSelecc, servSelecc2]))
    reservas_existentes = Reserva.objects.filter(fecha_res=fechaDeseada) if fechaDeseada else Reserva.objects.none()
    horas_disponibles = calcular_horas_disponibles(servicioConcat, reservas_existentes)

    paso1display = 1
    if request.GET.get("continuar") == "1" and (servSelecc or servSelecc2) and fechaDeseada:
        paso1display = 0
    if request.GET.get("volver") == "1":
        paso1display = 1

    if request.method == "POST" and "reservar_hora" in request.POST:
        servicio = (request.POST.get("servicio") or "").strip()
        fecha_str = request.POST.get("fecha_reserva")
        hora_str = request.POST.get("hora")
        perro_id = request.POST.get("perro")

        if not servicio or not fecha_str or not hora_str or not perro_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("reservar_hora")
        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_dt = datetime.strptime(hora_str, "%H:%M:%S").time()
        except ValueError:
            messages.error(request, "Formato de fecha u hora inválido.")
            return redirect("reservar_hora")

        perroReserva = get_object_or_404(Canino, pk=perro_id)
        valor_res = PRECIOS.get(perroReserva.tamano_can, 20000)
        duracion = DURACIONES.get(servicio)

        if not duracion:
            messages.error(request, "Servicio inválido.")
            return redirect("reservar_hora")

        # Validación de duplicado: misma mascota, mismo servicio, misma fecha
        if Reserva.objects.filter(
            canino_id_res_id=perro_id,
            servicio_res=servicio,
            fecha_res=fecha_dt
        ).exists():
            messages.warning(request, f"Ya existe una reserva de '{servicio}' para esa mascota en {fecha_dt}.")
            return redirect("ver_reservas")

        inicio_nueva = datetime.combine(fecha_dt, hora_dt)
        fin_nueva = inicio_nueva + duracion

        try:
            with transaction.atomic():
                reservas_withAtomic = Reserva.objects.select_for_update().filter(fecha_res=fecha_dt)
                for r in reservas_withAtomic:
                    inicio_existente = datetime.combine(r.fecha_res, r.hora_res)
                    fin_existente = inicio_existente + DURACIONES.get(r.servicio_res, timedelta())
                    if inicio_nueva < fin_existente and fin_nueva > inicio_existente:
                        raise ValidationError("😔 Esa hora ya fue reservada. Elige otra.")

                reserva_nueva = Reserva.objects.create(
                    servicio_res=servicio,
                    hora_res=hora_dt,
                    fecha_res=fecha_dt,
                    medio_pago_res="Efectivo",
                    valor_res=valor_res,
                    confirm_pago_res=False,
                    cliente_id_res_id=cliente_id,
                    canino_id_res_id=perro_id,
                )
                messages.success(request, "✅ Reserva creada correctamente")
                request.session["ultima_reserva_id"] = reserva_nueva.pk
                return redirect("home")

        except ValidationError as e:
            messages.error(request, e.message)
        except IntegrityError:
            messages.error(request, "💻💥 Error inesperado. Intenta de nuevo.")

    return render(request, "reservas/reserva.html", {
        "res_x_fecha": reservas_existentes,
        "fechaDeseada": fechaDeseada,
        "servSelecc": servSelecc,
        "servSelecc2": servSelecc2,
        "servicioConcat": servicioConcat,
        "horas_disponibles": horas_disponibles,
        "perros_cli": perros_cli,
        "paso1display": paso1display,
        "diccionario_serv1": SERVICIOS_VALIDOS.get(servSelecc, ""),
        "diccionario_serv2": SERVICIOS_VALIDOS.get(servSelecc2, ""),
        "fechaD_formateada": "-".join(reversed(fechaDeseada.split("-"))) if fechaDeseada else "",
    })

@requiere_login
def ver_reservas(request):
    cliente_id = request.session["cliente_id"]
    fechaActual = timezone.localtime().date()
    horaActual = timezone.localtime().time()

    reservasACancelar = Reserva.objects.filter(
        Q(fecha_res__gt=fechaActual) |
        Q(fecha_res=fechaActual, hora_res__gte=horaActual),
        cliente_id_res_id=cliente_id
    ).order_by("fecha_res", "hora_res")

    if request.method == "POST" and "cancelar_reserva" in request.POST:
        reserva = get_object_or_404(Reserva, pk=request.POST.get("reserva_id"), cliente_id_res_id=cliente_id)
        reserva.delete()
        messages.success(request, "Reserva cancelada correctamente ✅")

    reserva_id = request.session.pop("ultima_reserva_id", None)
    ultima_reserva = Reserva.objects.filter(pk=reserva_id, cliente_id_res_id=cliente_id).first() if reserva_id else None

    return render(request, "reservas/ver_reservas.html", {
        "reservasACancelar": reservasACancelar,
        "ultima_reserva": ultima_reserva,
    })

def servicios(request):
    today = timezone.localdate().strftime("%Y-%m-%d")
    return render(request, 'reservas/servicios.html', {"today": today})

def logout_cliente(request):
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente ✅")
    return redirect("home")

@requiere_login
def mis_mascotas(request):
    cliente_id = request.session["cliente_id"]
    mascotas = Canino.objects.filter(cliente_id_can_id=cliente_id).order_by("nombre_can")
    return render(request, "reservas/mis_mascotas.html", {"mascotas": mascotas})

@requiere_login
def editar_mascota(request, pk):
    cliente_id = request.session["cliente_id"]
    canino = get_object_or_404(Canino, pk=pk, cliente_id_can_id=cliente_id)
    form = RegistroDeCaninoForm(request.POST or None, instance=canino)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mascota actualizada correctamente ✅")
        return redirect("mis_mascotas")

    return render(request, "reservas/editar_mascota.html", {"form": form, "canino": canino})

@requiere_login
def historial_reservas(request):
    cliente_id = request.session["cliente_id"]
    fechaActual = timezone.localdate()
    reservas_pasadas = Reserva.objects.filter(
        cliente_id_res_id=cliente_id,
        fecha_res__lt=fechaActual
    ).order_by("-fecha_res", "-hora_res")

    return render(request, "reservas/historial_reservas.html", {
        "reservas_pasadas": reservas_pasadas
    })
