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
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth


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

        # 🔑 Si NO existe ningún dueño aún, este será el primero
        from .models import Cliente  # por si arriba no está importado
        if not Cliente.objects.filter(is_owner=True).exists():
            cliente.is_owner = True

        cliente.save()
        if cliente.is_owner:
            messages.success(request, "¡Cuenta creada con éxito! Has sido configurado como administrador de la tienda 👑")
        else:
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
            request.session["es_owner"] = cli.is_owner
            
            if cli.is_owner:
                messages.success(request, f"Bienvenido al panel administrativo, {cli.nombres_cli}! 👑")
                return redirect("admin_dashboard")
            
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

# views.py
from django.contrib.auth.decorators import login_required

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import messages

@requiere_login
def admin_dashboard(request):
    cliente_id = request.session["cliente_id"]
    cli = get_object_or_404(Cliente, pk=cliente_id)

    if not getattr(cli, "is_owner", False):
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("home")

    filtro = request.GET.get("filtro", "hoy")  # 'hoy' por defecto
    fecha_str = request.GET.get("fecha", "")

    hoy = timezone.localdate()

    # queryset base
    reservas = Reserva.objects.all().select_related("cliente_id_res", "canino_id_res")
    titulo_reservas = "Todas las reservas"

    # ---- FILTROS ----
    if filtro == "hoy":
        reservas = reservas.filter(fecha_res=hoy)
        titulo_reservas = "Reservas de hoy"

    elif filtro == "manana":
        manana = hoy + timedelta(days=1)
        reservas = reservas.filter(fecha_res=manana)
        titulo_reservas = "Reservas de mañana"

    elif filtro == "semana":
        fin_semana = hoy + timedelta(days=7)
        reservas = reservas.filter(fecha_res__range=(hoy, fin_semana))
        titulo_reservas = "Reservas próximos 7 días"

    elif filtro == "todas":
        titulo_reservas = "Todas las reservas"

    elif filtro == "fecha":
        if fecha_str:
            # Para DateField Django acepta 'YYYY-MM-DD' directamente, sin parsear
            reservas = reservas.filter(fecha_res=fecha_str)
            titulo_reservas = f"Reservas del {fecha_str}"
        else:
            reservas = reservas.none()
            titulo_reservas = "Selecciona una fecha para ver reservas"

    else:
        # Cualquier cosa rara ⇒ volvemos a hoy
        reservas = reservas.filter(fecha_res=hoy)
        titulo_reservas = "Reservas de hoy"

    reservas = reservas.order_by("fecha_res", "hora_res")

    return render(request, "reservas/admin_dashboard.html", {
        "cliente": cli,
        "reservas": reservas,
        "titulo_reservas": titulo_reservas,
        "filtro": filtro,
        "fecha_str": fecha_str,
    })

def gestionar_productos(request):
    if not request.user.is_owner:
        return redirect("home")  # Solo los dueños pueden acceder
    # Lógica para gestionar productos
    return render(request, 'reservas/gestionar_productos.html')

def ver_estadisticas(request):
    if not request.user.is_owner:
        return redirect("home")  # Solo los dueños pueden acceder
    # Lógica para ver estadísticas (reservas, ventas, etc.)
    return render(request, 'reservas/ver_estadisticas.html')

def configuracion_tienda(request):
    if not request.user.is_owner:
        return redirect("home")  # Solo los dueños pueden acceder
    # Lógica para configuraciones del sistema
    return render(request, 'reservas/configuracion_tienda.html')



# ==========================
# Panel del dueño / admin
# ==========================

def es_duenio(cliente: Cliente) -> bool:
    # 🔁 Ajusta este correo al que quieras usar como dueño
    return cliente.email_cli.lower() == "diegoassd@gmail.com"


@requiere_login
def admin_dashboard(request):
    # === dueño logueado ===
    cliente_id = request.session["cliente_id"]
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    # usamos tu helper es_duenio() como antes
    if not es_duenio(cliente):
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("home")

    hoy = timezone.localdate()

    # ⚠️ por defecto: mostrar TODAS las reservas (como tú tenías)
    filtro = request.GET.get("filtro", "todas")
    fecha_str = request.GET.get("fecha", "")

    # queryset base para la tabla
    reservas_qs = Reserva.objects.select_related("cliente_id_res", "canino_id_res")
    reservas = reservas_qs
    titulo_reservas = "Todas las reservas"

    # ========= FILTROS PARA LA TABLA =========
    if filtro == "hoy":
        reservas = reservas_qs.filter(fecha_res=hoy)
        titulo_reservas = "Reservas de hoy"

    elif filtro == "manana":
        manana = hoy + timedelta(days=1)
        reservas = reservas_qs.filter(fecha_res=manana)
        titulo_reservas = "Reservas de mañana"

    elif filtro == "semana":
        fin_semana = hoy + timedelta(days=7)
        reservas = reservas_qs.filter(fecha_res__range=(hoy, fin_semana))
        titulo_reservas = "Reservas próximos 7 días"

    elif filtro == "todas":
        reservas = reservas_qs
        titulo_reservas = "Todas las reservas"

    elif filtro == "fecha":
        if fecha_str:
            reservas = reservas_qs.filter(fecha_res=fecha_str)
            titulo_reservas = f"Reservas del {fecha_str}"
        else:
            reservas = reservas_qs.none()
            titulo_reservas = "Selecciona una fecha para ver reservas"

    else:
        # cualquier cosa rara → nos vamos a todas
        reservas = reservas_qs
        titulo_reservas = "Todas las reservas"

    reservas = reservas.order_by("fecha_res", "hora_res")

    # ============================================================
    # ==========  BLOQUE DE REPORTES PARA EL ADMIN  ==============
    # ============================================================

    # 1) RAZAS MÁS CONCURRENTES (top 3)
    razas_top = (
        Reserva.objects.select_related("canino_id_res")
        .values("canino_id_res__raza_can")
        .annotate(total=Count("id_reserva"))
        .order_by("-total")[:3]
    )

    # 2) CLIENTES MÁS CONCURRENTES (top 3)
    clientes_top = (
        Reserva.objects.select_related("cliente_id_res")
        .values("cliente_id_res__nombres_cli", "cliente_id_res__apellidos_cli")
        .annotate(total=Count("id_reserva"))
        .order_by("-total")[:3]
    )

    # 3) INGRESOS DEL MES ACTUAL (solo pagadas)
    inicio_mes = hoy.replace(day=1)
    ingresos_mes = (
        Reserva.objects.filter(
            fecha_res__gte=inicio_mes,
            fecha_res__lte=hoy,
            confirm_pago_res=True,
        ).aggregate(total=Sum("valor_res"))["total"] or 0
    )

    # 4) INGRESOS POR MES (últimos 6 meses)
    ingresos_por_mes = (
        Reserva.objects.filter(confirm_pago_res=True)
        .annotate(mes=TruncMonth("fecha_res"))
        .values("mes")
        .annotate(total=Sum("valor_res"))
        .order_by("-mes")[:6]
    )

    return render(request, "reservas/admin_dashboard.html", {
        "cliente": cliente,               # 👈 tu variable original
        "reservas": reservas,             # 👈 lista filtrada pero compatible
        "titulo_reservas": titulo_reservas,
        "filtro": filtro,
        "fecha_str": fecha_str,
        # reportes:
        "razas_top": razas_top,
        "clientes_top": clientes_top,
        "ingresos_mes": ingresos_mes,
        "ingresos_por_mes": ingresos_por_mes,
    })

    
    
@requiere_login
def admin_reserva_detalle(request, pk):
    # dueño logueado
    cliente_id = request.session["cliente_id"]
    cli = get_object_or_404(Cliente, pk=cliente_id)

    # solo el dueño puede ver esta vista
    if not getattr(cli, "is_owner", False):
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("home")

    # cargamos la reserva con cliente y canino asociados
    reserva = get_object_or_404(
        Reserva.objects.select_related("cliente_id_res", "canino_id_res"),
        pk=pk
    )

    # ---- MANEJO DE FORMULARIOS (POST) ----
    if request.method == "POST":
        # Actualizar precio y/o medio de pago
        if "actualizar_precio" in request.POST:
            nuevo_valor = request.POST.get("valor_res")
            nuevo_medio = (request.POST.get("medio_pago_res") or "").strip()

            try:
                if nuevo_valor is not None:
                    nuevo_valor_int = int(nuevo_valor)
                    if nuevo_valor_int < 0:
                        raise ValueError("El valor no puede ser negativo.")
                    reserva.valor_res = nuevo_valor_int

                if nuevo_medio:
                    reserva.medio_pago_res = nuevo_medio

                reserva.save()
                messages.success(request, "Valor y/o medio de pago actualizados correctamente ✅")
            except ValueError:
                messages.error(request, "El valor ingresado no es válido. Debe ser un número entero positivo.")

            return redirect("admin_reserva_detalle", pk=pk)

        # Confirmar pago
        if "confirmar_pago" in request.POST:
            reserva.confirm_pago_res = True
            # Si quieres, podrías forzar un medio de pago aquí si está vacío
            if not reserva.medio_pago_res:
                reserva.medio_pago_res = "Efectivo"
            reserva.save()
            messages.success(request, "Pago confirmado correctamente ✅")
            return redirect("admin_reserva_detalle", pk=pk)

    cliente_res = reserva.cliente_id_res
    canino_res = reserva.canino_id_res

    return render(request, "reservas/admin_reserva_detalle.html", {
        "admin_cli": cli,           # dueño logueado
        "reserva": reserva,         # reserva
        "cliente_res": cliente_res, # cliente de la reserva
        "canino_res": canino_res,   # perro de la reserva
    })

