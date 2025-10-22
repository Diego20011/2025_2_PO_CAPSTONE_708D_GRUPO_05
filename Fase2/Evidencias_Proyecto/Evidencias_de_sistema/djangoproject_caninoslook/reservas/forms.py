from django import forms
from .models import Cliente, Canino
from django.core.exceptions import ValidationError #Crea excepciones y muestra mensajes en el template html.
import re #Librería estándar de Python (viene instalada por defecto) que te permite buscar, comparar o validar patrones de texto usando expresiones regulares (regex).


#| Tipo          | Clase base        | Cuándo se usa                                                   | Relación con el modelo            |
#| ------------- | ----------------- | --------------------------------------------------------------- | --------------------------------- |
#| **Form**      | `forms.Form`      | Cuando el formulario no está ligado a un modelo                 | ❌ No guarda datos automáticamente |
#| **ModelForm** | `forms.ModelForm` | Cuando quieres crear o editar un modelo de la base de datos     | ✅ Está conectado al modelo        |


#Creamos una class con el nombre que deseamos.
class RegistroDeClienteForm(forms.ModelForm):
    class Meta: #clase interna especial que se usa para configurar el comportamiento del modelo o del formulario donde está definida.
        #Cuando la defines dentro de un forms.ModelForm, class Meta: le dice a Django de qué modelo sacar los datos y qué campos incluir o excluir.
        model = Cliente #de qué modelo sacar los datos.
        fields = ['nombres_cli', 'apellidos_cli', 'email_cli', 'numero_cli', 'password'] #qué campos incluir o excluir.
        #labels se usa para cambiar el texto que aparece como etiqueta (label_tag) de cada campo del formulario en el HTML.
        labels = {"nombres_cli": "Nombre/s:",
                  "apellidos_cli": "Apellido/s",
                  "email_cli": "Email:",
                  "numero_cli": "Número:",
                  "password": "Contraseña:"}
        #widgets es un diccionario que le dice a Django qué HTML renderizar para cada campo del formulario y permite personalizar su apariencia o comportamiento.
        #attrs={} -> atributos HTML adicionales
        widgets = {
            "nombres_cli": forms.TextInput(attrs={"placeholder": "Escribe aquí tu/s nombre/s.",
                                                  "class": "form-control"}), 
            #form-control: clase CSS que se usa para dar estilo uniforme y profesional a los campos de formularios en HTML, como <input>, <select>, <textarea>, etc.
            #Le da un ancho del 100% (ocupa todo el contenedor).
            #Le agrega padding y margen uniformes.
            #Le aplica un borde suave y redondeado.
            #Cambia el color del borde al hacer foco (:focus), mostrando un borde azul o similar.
            #Asegura que sea accesible y consistente en todos los navegadores.

            "apellidos_cli": forms.TextInput(attrs={"placeholder": "Escribe aquí tu/s apellido/s.",
                                                    "class": "form-control"}),

            "email_cli": forms.TextInput(attrs={"placeholder": "Escribe aquí tu email.",
                                                "class": "form-control"}),

            "numero_cli": forms.TextInput(attrs={"placeholder": "Escribe aquí tu número de teléfono registrado en WhatsApp.",
                                                 "class": "form-control"}),

            "password": forms.PasswordInput(attrs={"placeholder": "Escribe aquí tu contraseña.",
                                                   "class": "form-control"}),}

        #Personalizar los mensajes de error de las validaciones básicas que vienen del models.py
        error_messages ={
            "nombres_cli":{
                "max_length": "Nombre/s debe tener menos de 30 caracteres.",
                "blank": "Nombre/s debe contener al menos un nombre o su apodo."},
            "apellidos_cli":{
                "max_length": "Apellido/s debe tener menos de 30 caracteres.",
                "blank": "Apellido/s debe contener al menos un apellido."}}

    #Explicando cleaned_data:
    #Primero, usa lo definido en models.py, Django revisa que los datos enviados cumplan las validaciones básicas del campo, es decir:
    #Si un campo está marcado como blank=False, verifica que no esté vacío.
    #Si es un EmailField, valida el formato del correo (@).
    #Si es un IntegerField, comprueba que sea un número.
    #Si el campo tiene max_length=50, verifica que no se exceda.
    #Si todos los campos básicos pasan su validación básica, Django crea un diccionario (cleaned_data) con los datos “limpios”. cleaned=limpiados.

    #Después de las validaciones básicas, Django busca dentro del formulario si existe una función llamada clean_<nombreDelCampo>().
    #la función clean_<nombreDelCampo>(), debe retornar el valor del campo al final de la función porque:
    #Django espera que el valor devuelto sea el valor final “limpio” del campo.
    def clean_nombres_cli(self):
        #aquí obtiene el nombre "limpio", es decir, que no este vacío y que no sobrepase los 30 caracteres, estos son definidos en models.py.
        nombre = self.cleaned_data.get('nombres_cli') #nombres_cli viene de los nombres de los campos (fields) que defines arriba.
        #| Símbolo      | Significado                                           |
        #|--------------|-------------------------------------------------------|
        #| ^            | Indica inicio de la cadena                            |
        #| (?=...)      | asegura que el patrón dentro de (...) se cumpla.      |lookahead positivo (mirar por la ventana antes de salir.)(positivo quiere decir que está dentro).
        #| .            | Representa cualquier carácter (excepto salto de línea)|
        #| {3,}         | Mínimo caracteres del conjunto anterior               |
        #| [ ... ]      | Define un **conjunto de caracteres permitidos**       |
        #| A-Z          | Letras mayúsculas (A hasta Z)                         |
        #| a-z          | Letras minúsculas (a hasta z)                         |
        #| ÁÉÍÓÚáéíóúÑñ | Acentos y la letra ñ (tanto minúscula como mayúscula) |
        #|   (espacio)  | Permite espacios en el nombre                         |
        #| ( ... )*     | Grupo que puede repetirse cero o más veces            |
        #| $            | Indica fin de la cadena                               |
        if not re.match("^(?=.{3,}$)[A-Za-zÁÉÍÓÚáéíóúÑñ]+( [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$", nombre):
            #Esto garantiza:
            #No empieza ni termina con espacio.
            #No hay más de un espacio consecutivo.
            #Solo letras permitidas y 1 espacio entre palabras.
            #Mínimo 3 caracteres en total.
            raise ValidationError(["3-30 caracteres.",
                                  "Solo letras.",
                                  "Solo un espacio entre palabras"])
            #raise se usa para lanzar una excepción (frena el código). Luego se ocupa en el html como mensaje de error, sin antes definir en views.py.
            #Django lo quita del diccionario cleaned_data porque el campo no es válido.
        return nombre

    def clean_apellidos_cli(self):
        apellido = self.cleaned_data.get('apellidos_cli').strip() # strip le quita espacios al inicio y al final.
        if not re.match("^(?=.{3,}$)[A-Za-zÁÉÍÓÚáéíóúÑñ]+( [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$", apellido):
            raise ValidationError(["3-30 caracteres.",
                                  "Solo letras.",
                                  "Solo un espacio entre palabras"])
        return apellido

    def clean_email_cli(self):
        email = self.cleaned_data.get('email_cli').strip() # strip le quita espacios al inicio y al final.
        if Cliente.objects.filter(email_cli=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        if not re.match(r"^[A-Za-z0-9]+(\.[A-Za-z0-9]+)*@[A-Za-z0-9]+\.[A-Za-z]{2,}$", email): #\. = punto (.).
            raise ValidationError("El correo no es válido.")
        return email

    def clean_numero_cli(self):
        numero = self.cleaned_data.get('numero_cli').strip() # strip le quita espacios al inicio y al final.
        if not re.match("^[0-9]{8}$", numero): #Verifica que el número contenga 8 digitos juntos, es decir, sin espacios entre los digitos.
            raise ValidationError("El número debe contener 8 digitos sin espacios entre si.")
        numero569 = "+569"+self.cleaned_data.get('numero_cli')
        if Cliente.objects.filter(numero_cli=numero569).exists():
            raise ValidationError("Este número ya está registrado.")
        return numero569

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
            raise ValidationError(["Mínimo 8 caracteres.",
                                    "1 mayúscula.",
                                    "1 minúscula.",
                                    "1 número."])
        return password


class CaninoForm(forms.ModelForm):
    class Meta:
        model = Canino
        fields = ["nombre_can", "fecha_nac_can", "raza_can", "peso_can", "tamano_can", "cuidados_esp_can"]
        labels = {
            "nombre_can": "Nombre",
            "fecha_nac_can": "Fecha de nacimiento, nos puede tirar error, hay que arreglar html",
            "raza_can": "Raza",
            "peso_can": "Peso (kg)",
            "tamano_can": "Tamaño",
            "cuidados_esp_can": "Cuidados especiales",
        }
        widgets = {
            "nombre_can": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del perro"}),
            "fecha_nac_can": forms.DateInput(attrs={"class": "form-control", "placeholder": "Fecha de nacimiento"}),
            "raza_can": forms.TextInput(attrs={"class": "form-control", "placeholder": "Raza"}),
            "peso_can": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Peso en kg"}),
            "tamano_can": forms.TextInput(attrs={"class": "form-control", "placeholder": "Pequeño, mediano, grande"}),
            "cuidados_esp_can": forms.Textarea(attrs={"class": "form-control", "placeholder": "Indica cuidados especiales", "rows": 3}),
        }