from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import Cliente, Reserva
from datetime import datetime, timedelta


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

def reserva(request):
    #Obtener valor de select, su name="servicio"
    servSelecc = request.GET.get('servicio')

    #Obtener fecha de input, su name="fecha_reserva".
    fechaDeseada = request.GET.get('fecha_reserva')
    #Formateamos fecha de yyyy-mm-dd a dd-mm-yyyy para mostrarla bien en html.
    fechaD_formateada = ""
    if fechaDeseada:
        fechaD_formateada = "-".join(reversed(fechaDeseada.split("-")))

    #Consulta a la base de datos con fecha sin formatear, ordenamos la consulta para que esten los más tempranos primero.
    res_x_fecha = Reserva.objects.filter(fecha_res=fechaDeseada).order_by('hora_res')

    #Creamos lista de horas cada 30min desde las 9am - 17:30pm ("09:00:00", "09:30:00"...).
    lista_horas_full = [f"{h:02d}:{m:02d}:00" for h in range(9, 18) for m in (0, 30)]
    horasTo_baño = []
    horasTo_corte= []
    horasD_baño = []
    horasD_corte= []
    #Creamos las horas disponibles comparando las horas que están tomadas con las horas predeterminadas, agregando a lista_horasD solo las disponibles.
    #Baño=1h, Corte=3h.

    #PRUEBA, conclusion: cuando se ejecuta del sobre la lista, efectivamente el len de la lista cambia.
    #a=0
    #listaP=[0,1,2]
    #while a < len(listaP):
    #    del listaP[0]
    #    jeje=len(listaP)
    #    a=4 


    #Este código se encarga de mostrar los horarios disponibles
    if res_x_fecha.exists():
        i = 0 #i pq si.
        c = 0 #c de consulta
        #Este código recorre la lista_horas_full (full disponibilidad) y también recorre la lista de la consulta (a la base de datos que trae las reservas hechas).
        #Entonces, dependiendo del servicio, al coincidir horas elimina 2 (baño) o 6 (corte) items (horas/reservas) de la lista full, incluyendo al que coincide.
        while i < len(lista_horas_full) and c < len(res_x_fecha):
            #Recordar: la consulta viene ordenada del más temprano.
            #Si coinciden las horas, entramos a eliminar dependiendo del servicio. Pero, sin antes asegurarnos de que existe la reserva, para que no nos salte error: fuera de indice.
            while lista_horas_full[i] == res_x_fecha[c].hora_res.strftime("%H:%M:%S"):
                if res_x_fecha[c].servicio_res == "Baño":
                    del lista_horas_full[i:i+2]  #borra el actual y 1 más. Al borrar el actual y otros más, se posiciona un nuevo item/hora en i. Es decir, i itera.
                elif res_x_fecha[c].servicio_res == "Corte":
                    del lista_horas_full[i:i+6] # borra el actual y 5 más. Al borrar el actual y otros más, se posiciona un nuevo item/hora en i. Es decir, i avanza al siguiente item.
                c = c+1 #Entonces al tener una nueva hora en la lista_full[i] ya no va a coincidir con la hora de la reserva en el while, entonces, tenemos que ir a la siguiente reserva.
                if c >= len(res_x_fecha):
                    break
            i = i+1 #Si la siguiente reserva (c+1) no coincide con la hora actual de i, avanzamos en la lista de i.

        horasTo_baño = lista_horas_full
        horasTo_corte = lista_horas_full

        #Este código se encarga de descartar las horas que no son posibles por el tiempo del servicio. Me explico:
        #El código anterior elimina el actual y los siguientes dependiendo del servicio, pero, que pasa con el anterior. Ej: hay una reserva para baño a las 10, el código anterior
        #va a eliminar el item de las 10:00:00 y de las 10:30:00, pero, no va a eliminar el item de las 9, entonces los usuarios van a poder seleccionar a las 9 para corte, cosa que esta mal.

        #EN VEZ DE QUE SELECCIONE UN SERVICIO PARA MOSTRAR LAS HORAS DE ESE SERVICIO, PODEMOS MOSTRAR AMBOS A LA VEZ! ¿COMO? NOSE XD, PENSAR EN ELLO, RECORDAR QUE ES PARA MOVILES MAYORMENTE!
        #PODRIAMOS MOSTRAR ITEMS ORDENADOS POR HORA, EL ITEM QUE TENGA EL TIPO DE SERVICIO Y LA HORA, PODRIAMOS TENER IMAGENES DE TIJERAS O BURBUJAS O AMBAS PARA EL CORTE.
        #PODRIAMOS MOSTRAR AMBOS EN UNA FILA HACIA ABAJO.
        #RECORDAR QUE LA DUEÑA DEBE ELEGIR SI HABILITA EL DIA PARA TRABAJO O NO.

        q = 0 #q de quitar
        q2 = 0
        if servSelecc == "baño":
            while q+1 < len(horasTo_baño):
                #      datetime.strptime convierte hora en datetime para poder sumarle o restarle minutos.
                if (datetime.strptime(horasTo_baño[q], "%H:%M:%S") + timedelta(minutes=30)).strftime("%H:%M:%S") == horasTo_baño[q+1]: #.strftime("%H:%M:%S") convierte hora en string.
                    horasD_baño.append(horasTo_baño[q]) #Agregamos si coinciden las horas, ya que, significa que está disponible esa media hora que necesitamos para el baño.
                q = q+1

        if servSelecc == "corte":
            while q2+5 < len(horasTo_corte):
                if ((datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(minutes=30)).strftime("%H:%M:%S") == horasTo_corte[q2+1]
                and (datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(hours=1)).strftime("%H:%M:%S") == horasTo_corte[q2+2]
                and (datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(hours=1, minutes=30)).strftime("%H:%M:%S") == horasTo_corte[q2+3]
                and (datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(hours=2)).strftime("%H:%M:%S") == horasTo_corte[q2+4]
                and (datetime.strptime(horasTo_corte[q2], "%H:%M:%S") + timedelta(hours=2, minutes=30)).strftime("%H:%M:%S") == horasTo_corte[q2+5]):
                    horasD_corte.append(horasTo_corte[q2]) #Agregamos si coinciden las horas, ya que, significa que están disponibles las 2 horas y media.
                q2 = q2+1
            
    else:
        horasD_baño = lista_horas_full
        horasD_corte = lista_horas_full

    return render(request, "reservas/reserva.html", {"res_x_fecha": res_x_fecha, "fechaD_formateada": fechaD_formateada, "servSelecc": servSelecc, "horasD_baño": horasD_baño, "horasD_corte": horasD_corte})