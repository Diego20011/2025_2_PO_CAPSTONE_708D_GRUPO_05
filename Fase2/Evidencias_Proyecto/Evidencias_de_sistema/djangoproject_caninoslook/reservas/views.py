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
from django.conf import settings
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from django.urls import reverse
from django.core.mail import send_mail

from django.core.mail import EmailMultiAlternatives

# ==========================
# Constantes
# ==========================
DURACIONES = {
    "Baño": timedelta(minutes=45),
    "Corte de pelo": timedelta(hours=2),
    "Corte de uñas": timedelta(minutes=15),
    "Limpieza de oido": timedelta(minutes=15),
    "Estética full": timedelta(hours=2, minutes=45),
}


PRECIOS = {
    'Pequeño': 20000,
    'Mediano': 25000,
    'Grande': 30000,
}

SERVICIOS_VALIDOS = {
    "Baño": "Baño",
    "Corte de pelo": "Corte de pelo",
    "Corte de uñas": "Corte de uñas",
    "Limpieza de oido": "Limpieza de oido",
    "Estética full": "Estética full"
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
def obtener_duracion_total(servicio_str):
    """
    Acepta por ejemplo:
      - "Baño"
      - "Baño + Corte de pelo"
      - "Baño + Corte de pelo + Deslanado"
    y devuelve la suma de DURACIONES de cada servicio válido.
    """
    if not servicio_str:
        return None

    # Separa por '+'
    partes = [p.strip() for p in servicio_str.split("+") if p.strip()]

    dur_total = timedelta()
    valido = False

    for p in partes:
        # p debe coincidir con las claves de DURACIONES, ej: "Baño", "Corte de pelo"
        if p in DURACIONES:
            dur_total += DURACIONES[p]
            valido = True

    return dur_total if valido else None


def calcular_horas_disponibles(servicioConcat, reservas_existentes):
    # Generar todas las horas cada 15 minutos entre 09:00 y 18:00
    lista_horas_full = [
        f"{h:02d}:{m:02d}:00"
        for h in range(9, 18)
        for m in (0, 15, 30, 45)
    ]
    lista_horas_full.append("18:00:00")  # cierre del día

    # 1) Bloquear los bloques ya reservados
    if reservas_existentes.exists():
        for reserva in reservas_existentes:
            duracion_existente = obtener_duracion_total(reserva.servicio_res)
            if not duracion_existente:
                continue

            # bloques de 15 minutos
            bloques_ocupados = int(duracion_existente.total_seconds() / 900)
            try:
                idx_inicio = lista_horas_full.index(
                    reserva.hora_res.strftime("%H:%M:%S")
                )
            except ValueError:
                # Si por alguna razón la hora no está en la lista, la ignoramos
                continue

            # Eliminar de la grilla los bloques ocupados por esta reserva
            del lista_horas_full[idx_inicio:idx_inicio + bloques_ocupados]

    horas_disponibles = []

    # 2) Ahora, según lo que el cliente quiere reservar (servicioConcat),
    #    calculamos qué horas son posibles
    duracion_nueva = obtener_duracion_total(servicioConcat)
    if duracion_nueva:
        bloques_necesarios = int(duracion_nueva.total_seconds() / 900)

        for i in range(len(lista_horas_full) - bloques_necesarios):
            # Verificamos que haya bloques consecutivos suficientes
            try:
                inicio = datetime.strptime(lista_horas_full[i], "%H:%M:%S")
            except ValueError:
                continue

            es_valido = True
            for j in range(1, bloques_necesarios):
                esperado = (inicio + timedelta(minutes=15 * j)).strftime("%H:%M:%S")
                if lista_horas_full[i + j] != esperado:
                    es_valido = False
                    break

            if es_valido:
                horas_disponibles.append(lista_horas_full[i])

    # Si por algún motivo no se pudo calcular (o no hay servicio todavía),
    # devolvemos la grilla completa como fallback
    return horas_disponibles or lista_horas_full


def obtener_precio_total(servicio_str, tamano_can):
    """
    Calcula el valor de la reserva según:
    - tamaño del canino (usa PRECIOS como base)
    - cantidad de servicios seleccionados
    """
    if not servicio_str:
        return 0

    partes = [p.strip() for p in servicio_str.split("+") if p.strip()]
    servicios_validos = [p for p in partes if p in SERVICIOS_VALIDOS]

    if not servicios_validos:
        return 0

    # Precio base según tamaño del perro
    base = PRECIOS.get(tamano_can, 20000)

    # Versión simple: multiplicar por la cantidad de servicios
    cantidad = len(servicios_validos)
    valor_total = base * cantidad

    return valor_total

# ==========================
# Vistas
# ==========================

def registrar_cliente(request):
    form = RegistroDeClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cliente = form.save(commit=False)
        cliente.password_cli = make_password(form.cleaned_data["password_cli"])

        # Si no existe ningún dueño aún, este será el primero
        if not Cliente.objects.filter(is_owner=True).exists():
            cliente.is_owner = True

        cliente.email_verificado = False  # 👈 aún no verifica correo
        cliente.save()

        # ========= ENVIAR CORREO DE ACTIVACIÓN (HTML BONITO) =========
        token = dumps(cliente.pk, salt="activar-correo")
        url_activacion = request.build_absolute_uri(
            reverse("activar_cuenta", args=[token])
        )

        # URL absoluta al logo estático
        logo_path = ("reservas/images/logo_caninoslook.png")
        logo_url = request.build_absolute_uri(logo_path)

        asunto = "Activa tu cuenta en CaninosLook"

        # Versión texto plano (por si el cliente no soporta HTML)
        text_content = (
            f"Hola {cliente.nombres_cli},\n\n"
            f"Gracias por registrarte en CaninosLook.\n"
            f"Para activar tu cuenta, abre este enlace:\n\n"
            f"{url_activacion}\n\n"
            f"Si tú no creaste esta cuenta, puedes ignorar este correo."
        )

        # Versión HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="utf-8">
          <title>Activa tu cuenta</title>
        </head>
        <body style="margin:0; padding:0; background-color:#f5f5f5; font-family:Arial, sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5; padding:20px 0;">
            <tr>
              <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden;">
                  <tr>
                    <td style="background-color:#ff914d; padding:16px 24px; text-align:center;">
                      <img src="{logo_url}" alt="CaninosLook" style="max-height:60px; display:block; margin:0 auto;">
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:24px;">
                      <h2 style="margin:0 0 16px 0; color:#333333;">¡Hola, {cliente.nombres_cli}! 🐶✨</h2>
                      <p style="margin:0 0 12px 0; color:#555555; line-height:1.5;">
                        Gracias por registrarte en <strong>CaninosLook</strong>. Antes de poder usar tu cuenta,
                        necesitamos que confirmes que este correo te pertenece.
                      </p>
                      <p style="margin:0 0 12px 0; color:#555555; line-height:1.5;">
                        Haz clic en el siguiente botón para <strong>activar tu cuenta</strong>:
                      </p>
                      <p style="text-align:center; margin:24px 0;">
                        <a href="{url_activacion}"
                           style="
                             background-color:#ff914d;
                             color:#ffffff;
                             text-decoration:none;
                             padding:12px 24px;
                             border-radius:6px;
                             font-weight:bold;
                             display:inline-block;
                           ">
                          Activar cuenta
                        </a>
                      </p>
                      <p style="margin:0 0 8px 0; color:#777777; font-size:13px; line-height:1.5;">
                        Si el botón no funciona, también puedes copiar y pegar este enlace en tu navegador:
                      </p>
                      <p style="margin:0 0 16px 0; color:#777777; font-size:13px; word-break:break-all;">
                        {url_activacion}
                      </p>
                      <p style="margin:0; color:#aaaaaa; font-size:12px; line-height:1.5;">
                        Si tú no creaste esta cuenta, puedes ignorar este correo.
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="background-color:#f0f0f0; padding:12px 24px; text-align:center; color:#999999; font-size:12px;">
                      &copy; {timezone.now().year} CaninosLook. Todos los derechos reservados.
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@caninoslook.local")

        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,            
            from_email=from_email,
            to=[cliente.email_cli],      
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        messages.success(
            request,
            "¡Cuenta creada con éxito! Te enviamos un enlace de activación a tu correo. "
            "Debes activarla antes de iniciar sesión. ✅"
        )
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

        # 👇 Nuevo: bloquear si no ha verificado el correo
        if not cli.email_verificado:
            messages.error(
                request,
                "Tu correo aún no está verificado. Revisa tu bandeja de entrada y haz clic en el enlace de activación."
            )
            return render(request, "reservas/login.html")

        if check_password(password, cli.password_cli):
            request.session["cliente_id"] = cli.pk
            request.session["cliente_nombre"] = cli.nombres_cli
            request.session["is_owner"] = cli.is_owner
            if cli.is_owner:
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

    servicios_seleccionados = request.GET.getlist("servicio")
    servicios_seleccionados = [s for s in servicios_seleccionados if s in SERVICIOS_VALIDOS]

    fechaDeseada = request.GET.get("fecha_reserva")
    servicioConcat = " + ".join(servicios_seleccionados)

    reservas_existentes = Reserva.objects.filter(fecha_res=fechaDeseada) if fechaDeseada else Reserva.objects.none()
    horas_disponibles = calcular_horas_disponibles(servicioConcat, reservas_existentes)

    paso1display = 1
    if request.GET.get("continuar") == "1" and servicios_seleccionados and fechaDeseada:
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

        duracion = obtener_duracion_total(servicio)

        valor_res = obtener_precio_total(servicio, perroReserva.tamano_can)
        if not duracion:
            messages.error(request, "Servicio inválido.")
            return redirect("reservar_hora")

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
                    dur_exist = obtener_duracion_total(r.servicio_res) or timedelta()
                    fin_existente = inicio_existente + dur_exist

                    if inicio_nueva < fin_existente and fin_nueva > inicio_existente:
                        raise ValidationError("😔 Esa hora ya fue reservada. Elige otra.")

                servicio_db = (servicio or "").strip()[:250]

                reserva_nueva = Reserva.objects.create(
                    servicio_res=servicio_db,
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
        "servicioConcat": servicioConcat,
        "horas_disponibles": horas_disponibles,
        "perros_cli": perros_cli,
        "paso1display": paso1display,
        "diccionario_serv": servicioConcat,
        "fechaD_formateada": "-".join(reversed(fechaDeseada.split("-"))) if fechaDeseada else "",
        "servicios_seleccionados": servicios_seleccionados,
        "SERVICIOS_VALIDOS": SERVICIOS_VALIDOS,
    })



@requiere_login
def ver_reservas(request):
    cliente_id = request.session["cliente_id"]
    fechaActual = timezone.localtime().date()
    horaActual = timezone.localtime().time()

    confCancelarR=0
    if request.GET.get("confCancelarR"):
        confCancelarR=1
        reservasACancelar = Reserva.objects.filter(pk=request.GET.get("confCancelarR"))
    else:
        reservasACancelar = Reserva.objects.filter(
        Q(fecha_res__gt=fechaActual) |
        Q(fecha_res=fechaActual, hora_res__gt=horaActual) |
        Q(confirm_pago_res=0) | Q(confirm_pago_res=1),
        cliente_id_res_id=cliente_id
        ).order_by("confirm_pago_res", "fecha_res", "hora_res")

    if request.method == "POST" and "cancelar_reserva" in request.POST:
        reserva = get_object_or_404(Reserva, pk=request.POST.get("reserva_id"), cliente_id_res_id=cliente_id)
        reserva.delete()
        messages.success(request, "Reserva cancelada correctamente ✅")
        return redirect("ver_reservas")

    reserva_id = request.session.pop("ultima_reserva_id", None)
    ultima_reserva = Reserva.objects.filter(pk=reserva_id, cliente_id_res_id=cliente_id).first() if reserva_id else None

    return render(request, "reservas/ver_reservas.html", {
        "reservasACancelar": reservasACancelar,
        "ultima_reserva": ultima_reserva,
        "confCancelarR": confCancelarR
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
    horaActual = timezone.localtime().time()

    reservas_pasadas = Reserva.objects.filter(
        cliente_id_res_id=cliente_id,
        confirm_pago_res=True,
        fecha_res__lte=fechaActual  # 👈 incluye hoy completo
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

##def es_duenio(cliente: Cliente) -> bool:
    # 🔁 Ajusta este correo al que quieras usar como dueño
    return cliente.email_cli.lower() == "diegoassd@gmail.com"


@requiere_login
def admin_dashboard(request):
    # === dueño logueado ===
    cliente_id = request.session["cliente_id"]
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    # usamos tu helper es_duenio() como antes
    if not cliente.is_owner:
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("home")
    # 👇 Aquí manejamos la cancelación antes de armar los filtros
    if request.method == "POST" and "cancelar_admin" in request.POST:
        reserva_id = request.POST.get("reserva_id")
        reserva = get_object_or_404(Reserva, pk=reserva_id)
        reserva.delete()
        messages.success(request, "Reserva cancelada correctamente ✅")
        return redirect("admin_dashboard")
    

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

def activar_cuenta(request, token):
    try:
        cliente_id = loads(token, salt="activar-correo", max_age=60 * 60 * 24 * 3)  # 3 días
    except SignatureExpired:
        messages.error(request, "El enlace de activación ha expirado. Regístrate nuevamente.")
        return redirect("crear_cuenta")
    except BadSignature:
        messages.error(request, "Enlace de activación inválido.")
        return redirect("login")

    cliente = get_object_or_404(Cliente, pk=cliente_id)

    if cliente.email_verificado:
        messages.info(request, "Tu cuenta ya estaba activada. Ahora puedes iniciar sesión.")
    else:
        cliente.email_verificado = True
        cliente.save()
        messages.success(request, "Correo verificado correctamente. Ahora puedes iniciar sesión. ✅")

    return redirect("login")
