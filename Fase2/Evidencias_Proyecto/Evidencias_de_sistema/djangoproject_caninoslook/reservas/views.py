from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import RegistroDeClienteForm, RegistroDeCaninoForm
from .models import Cliente, Reserva, Canino
from django.db import IntegrityError, transaction #Para manejar errores, Para atomic transaction.
from django.core.exceptions import ValidationError #Para manejar errores.
from django.db.models import Q #Para poner condiciones OR (|) y AND (&) en las consultas de filter.

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

    cliente = Cliente.objects.get(pk=cliente_id)

    return render(request, "reservas/home.html", {
        "reservas": reservas,
        "cliente": cliente
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
                                  #select_for_update(), 
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

    if request.method == "POST" and "reservar_hora" in request.POST: #reservar_hora es el name del <button>
        DURACIONES = {
            'Baño': timedelta(hours=1),
            'Corte': timedelta(hours=3)}
        inicio_nueva = datetime.combine(datetime.strptime(request.POST.get("fecha_reserva"), "%Y-%m-%d").date(), datetime.strptime(request.POST.get("hora"), "%H:%M:%S").time())
        duracion = DURACIONES.get(request.POST.get("servicio"))
        fin_nueva = inicio_nueva + duracion

        #SOLUCIÓN RESERVAS CONCURRENTES.
        try:
        #atomic() agrupa todas las consultas en un bloque “todo o nada”, si todo sale bien se aplican los camnios, sino, no.
        #Atomicidad:
        #Todo lo que ocurre dentro se ejecuta como una sola unidad.
        #Si algo falla (excepción, error, etc.), se revierte todo — como si no hubiera pasado nada.

        #Aislamiento temporal:
        #Ningún otro proceso ve tus cambios hasta que la transacción termina exitosamente (commit).

            with transaction.atomic(): #Permite utilizar select_for_update() que bloquea la lectura y escritura de las filas de la consulta hasta que se complete la transacción.
                # Obtenemos las reservas actuales con select_for_update.
                reservas_withAtomic = Reserva.objects.select_for_update().filter(fecha_res=request.POST.get("fecha_reserva"))
                #Explicación de comportamiento select_for_update() con 2 reservas concurrentes:
                #2 personas entran a reservar, reservan al mismo tiempo, el que llega primero a la bd es el que bloquea las consultas de lectura y escritura
                #para las filas de la consulta reservas_withAtomic, esto seguirá así hasta terminar de ejecutar el código dentro de with transaction.atomic():
                #Entonces, para la segunda persona habrá un delay o espera de 1 segundo más o menos mientras se ejecuta el código de la primera persona, ¿porque?
                #porque la consulta involucra las mismas líneas, entonces debe esperar ya que estan bloqueadas.
                #cuando se termina de ejecutar el código de with transaction.atomic(): de la 1era persona 
                #se ejecuta la consulta de la 2da persona que estaba esperando, con la diferencia que ahora en la consulta apareceran las filas que agrego A.
                #luego se ejecuta la lógica anti superposición de horas y si hay error lo lanza.
                if reservas_withAtomic:
                    for reserva in reservas_withAtomic:

                        inicio_existente = datetime.combine(reserva.fecha_res, reserva.hora_res)
                        duracion_existente = DURACIONES.get(reserva.servicio_res)
                        fin_existente = inicio_existente + duracion_existente

                        # Comprobación de superposición.
                        if inicio_nueva < fin_existente and fin_nueva > inicio_existente:
                            raise ValidationError("😔 Esa hora ya fue reservada. Elige otra. HEHE")

                        #Crear reserva nueva.
                        reserva_nueva = Reserva.objects.create(
                            servicio_res=request.POST.get("servicio"),
                            hora_res=datetime.strptime(request.POST.get("hora"), "%H:%M:%S").time(),
                            fecha_res=datetime.strptime(request.POST.get("fecha_reserva"), "%Y-%m-%d").date(),
                            medio_pago_res="Efectivo",
                            valor_res=0,
                            confirm_pago_res=0,
                            cliente_id_res_id=cliente_id,
                            canino_id_res_id=request.POST.get("perro"),
                        )
                        messages.success(request, "✅ Reserva creada correctamente")
                        request.session["ultima_reserva_id"] = reserva_nueva.pk
                else:
                    reserva_nueva = Reserva.objects.create(
                        servicio_res=request.POST.get("servicio"),
                        hora_res=request.POST.get("hora"),
                        fecha_res=request.POST.get("fecha_reserva"),
                        medio_pago_res="Efectivo",
                        valor_res=0,
                        confirm_pago_res=0,
                        cliente_id_res_id=cliente_id,
                        canino_id_res_id=request.POST.get("perro"),
                    )
                    messages.success(request, "✅ Reserva creada correctamente")
                    request.session["ultima_reserva_id"] = reserva_nueva.pk

        except IntegrityError as e:
            if "unique_fecha_hora" in str(e):
                messages.error(request, "😔 Esa hora ya fue reservada. Elige otra. uwu")
                print("error:", e)
            else:
                messages.error(request, "💻💥 Error inesperado. Intenta recargar la página o abrir el enlace en otra pestaña.")
                print("error:", e)
        except ValidationError as ve:
            messages.error(request, ve.message)

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
def ver_reservas(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        return redirect("login")

    fechaActual = timezone.localtime().date()
    horaActual = timezone.localtime().time()

    reservasACancelar = Reserva.objects.filter(
        Q(fecha_res__gt=fechaActual) | #gt=greather than, e=equal, Q es una libreria para | &.
        Q(fecha_res=fechaActual, hora_res__gte=horaActual), #fecha_res sea igual a fechaActual y hora_res sea mayor o igual que horaActual
        cliente_id_res_id=cliente_id
    ).order_by("fecha_res", "hora_res")

    #Eliminando reserva.
    if request.method == "POST" and "cancelar_reserva" in request.POST:
        Reserva.objects.filter(pk=request.POST.get("reserva_id")).delete()

    ultima_reserva = None
    reserva_id = request.session.pop("ultima_reserva_id", None)
    if reserva_id:
        try:
            ultima_reserva = Reserva.objects.get(pk=reserva_id, cliente_id_res_id=cliente_id)
        except Reserva.DoesNotExist:
            ultima_reserva = None

    return render(request, "reservas/ver_reservas.html", {
        "reservasACancelar": reservasACancelar,
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
