from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Cliente, Canino

# ==========================
# Regex y constantes centralizadas
# ==========================
REGEX_NOMBRE = r"^(?=.{3,30}$)[A-Za-zÁÉÍÓÚáéíóúÑñ]+( [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$"
REGEX_EMAIL = r"^[A-Za-z0-9]+(\.[A-Za-z0-9]+)*@[A-Za-z0-9]+\.[A-Za-z]{2,}$"
REGEX_NUMERO = r"^[0-9]{8}$"
REGEX_RAZA = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]+( [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$"
REGEX_CUIDADOS = r"^[0-9A-Za-zÁÉÍÓÚáéíóúÑñ \t\n¡!¿?.-]*$"

TAMANOS_VALIDOS = ["Pequeño", "Mediano", "Grande"]

RAZAS_CANINAS = [
    "Labrador Retriever", "Pastor Alemán", "Golden Retriever", "Bulldog Francés", "Beagle",
    "Poodle", "Chihuahua", "Boxer", "Pitbull", "Shih Tzu", "Dálmata", "Cocker Spaniel",
    "Border Collie", "Husky Siberiano", "Rottweiler", "Doberman", "Akita", "Bichón Frisé",
    "Terrier", "Maltés", "Pug", "Samoyedo", "Shar Pei", "Setter Irlandés", "San Bernardo"
]
PESOS_CANINOS = [
    ("1-5", "1 - 5 kg (pequeño)"),
    ("6-10", "6 - 10 kg"),
    ("11-20", "11 - 20 kg"),
    ("21-30", "21 - 30 kg"),
    ("31-40", "31 - 40 kg"),
    ("41+", "Más de 40 kg")
]



# ==========================
# Formularios
# ==========================

class RegistroDeClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombres_cli', 'apellidos_cli', 'email_cli', 'numero_cli', 'password_cli']
        labels = {
            "nombres_cli": "Nombre/s:",
            "apellidos_cli": "Apellido/s:",
            "email_cli": "Email:",
            "numero_cli": "Número:",
            "password_cli": "Contraseña:",
        }
        widgets = {
            "nombres_cli": forms.TextInput(attrs={"placeholder": "Ingresa nombre/s.", "class": "form-control"}),
            "apellidos_cli": forms.TextInput(attrs={"placeholder": "Ingresa apellido/s.", "class": "form-control"}),
            "email_cli": forms.EmailInput(attrs={"placeholder": "Ingresa email.", "class": "form-control"}),
            "numero_cli": forms.TextInput(attrs={"placeholder": "Ingresa tu número sin +569.", "class": "form-control"}),
            "password_cli": forms.PasswordInput(attrs={"placeholder": "Ingresa contraseña.", "class": "form-control"}),
        }

    def clean_nombres_cli(self):
        nombre = self.cleaned_data.get('nombres_cli', '').strip()
        if not re.match(REGEX_NOMBRE, nombre):
            raise ValidationError("Nombre inválido: 3-30 caracteres, solo letras y un espacio entre palabras.")
        return nombre

    def clean_apellidos_cli(self):
        apellido = self.cleaned_data.get('apellidos_cli', '').strip()
        if not re.match(REGEX_NOMBRE, apellido):
            raise ValidationError("Apellido inválido: 3-30 caracteres, solo letras y un espacio entre palabras.")
        return apellido

    def clean_email_cli(self):
        email = self.cleaned_data.get('email_cli', '').strip()
        if Cliente.objects.filter(email_cli=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        if not re.match(REGEX_EMAIL, email):
            raise ValidationError("Formato de correo inválido.")
        return email

    def clean_numero_cli(self):
        numero = self.cleaned_data.get('numero_cli', '').strip()
        if not re.match(REGEX_NUMERO, numero):
            raise ValidationError("El número debe contener exactamente 8 dígitos.")
        numero569 = "+569" + numero
        if Cliente.objects.filter(numero_cli=numero569).exists():
            raise ValidationError("Este número ya está registrado.")
        return numero569

    def clean_password_cli(self):
        password = self.cleaned_data.get('password_cli', '')
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
            raise ValidationError("La contraseña debe tener al menos 8 caracteres, incluir mayúscula, minúscula y número.")
        return password


class RegistroDeCaninoForm(forms.ModelForm):
    class Meta:
        model = Canino
        fields = ["nombre_can", "fecha_nac_can", "raza_can", "peso_can", "tamano_can", "cuidados_esp_can"]
        labels = {
            "nombre_can": "Nombre",
            "fecha_nac_can": "Fecha de nacimiento",
            "raza_can": "Raza",
            "peso_can": "Peso (kg)",
            "tamano_can": "Tamaño",
            "cuidados_esp_can": "Cuidados especiales",
        }
        widgets = {
            "nombre_can": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del perro"}),
            "fecha_nac_can": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "raza_can": forms.Select(
                choices=[(r, r) for r in RAZAS_CANINAS],
                attrs={"class": "form-select"}
            ),
            "peso_can": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ej: 12"}),
            "tamano_can": forms.Select(attrs={"class": "form-select"}),
            "cuidados_esp_can": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Cuidados especiales"}),
        }

    def clean_nombre_can(self):
        nombre = self.cleaned_data.get('nombre_can', '').strip()
        if not re.match(REGEX_NOMBRE, nombre):
            raise ValidationError("Nombre inválido: solo letras y un espacio entre palabras.")
        if len(nombre) > 20:
            raise ValidationError("El nombre no puede superar los 20 caracteres.")
        return nombre

    def clean_fecha_nac_can(self):
        fecha_nac = self.cleaned_data.get('fecha_nac_can')
        hoy = timezone.localdate()
        if fecha_nac > hoy:
            raise ValidationError("No puede registrar un perro que aún no nace.")
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        if edad > 25:
            raise ValidationError("El perro no puede tener más de 25 años.")
        return fecha_nac
    def clean_peso_can(self):
        peso = self.cleaned_data.get('peso_can')
        if peso <= 0 or peso > 99:
            raise ValidationError("El peso debe ser un número entre 1 y 99 kg.")
        return peso




    def clean_tamano_can(self):
        tamaño = self.cleaned_data.get('tamano_can')
        if tamaño not in TAMANOS_VALIDOS:
            raise ValidationError("Selecciona un tamaño válido: Pequeño, Mediano o Grande.")
        return tamaño

    def clean_cuidados_esp_can(self):
        cuida_esp = self.cleaned_data.get('cuidados_esp_can', '')
        if not re.match(REGEX_CUIDADOS, cuida_esp):
            raise ValidationError("Caracteres permitidos: letras, números y signos básicos (¡!¿?.-).")
        if len(cuida_esp) > 1000:
            raise ValidationError("Excediste el máximo de 1000 caracteres.")
        return cuida_esp
# Otros formularios pueden ser añadidos aquí siguiendo el mismo patrón.