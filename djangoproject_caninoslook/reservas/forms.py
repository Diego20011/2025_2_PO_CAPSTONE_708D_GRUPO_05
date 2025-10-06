# reservas/forms.py
from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from .models import Cliente

telefono_validator = RegexValidator(
    regex=r'^\d{1,9}$',
    message="Ingresa un número válido de máximo 9 dígitos"
)

class ClienteForm(forms.ModelForm):
    numero_cli = forms.CharField(
        validators=[telefono_validator],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: 912345678",
            "maxlength": "9",
            "inputmode": "numeric",
            "pattern": r"\d*"
        })
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        label="Repetir contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Cliente
        fields = ["nombres_cli", "apellidos_cli", "email_cli", "numero_cli"]
        labels = {
            "nombres_cli": "Nombre/s",
            "apellidos_cli": "Apellido/s",
            "email_cli": "Email",
            "numero_cli": "Número",
        }
        widgets = {
            "nombres_cli": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingresa tu nombre"
            }),
            "apellidos_cli": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingresa tu apellido"
            }),
            "email_cli": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "ejemplo@email.com"
            }),
        }

    def clean_email_cli(self):
        email = self.cleaned_data.get("email_cli")
        if Cliente.objects.filter(email_cli=email).exists():
            raise forms.ValidationError("Este email ya está registrado")
        return email

    def clean_numero_cli(self):
        numero = self.cleaned_data.get("numero_cli")
        if Cliente.objects.filter(numero_cli=numero).exists():
            raise forms.ValidationError("Este número ya está registrado")
        return numero

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.password = make_password(self.cleaned_data["password1"])
        if commit:
            obj.save()
        return obj