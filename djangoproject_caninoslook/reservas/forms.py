from django import forms
from .models import Cliente
from django.core.validators import RegexValidator

telefono_validator = RegexValidator(
    regex=r'^\d{1,9}$',
    message="Ingresa un número válido de máximo 9 dígitos"
)

class ClienteForm(forms.ModelForm):
    numero_cli = forms.CharField(
        validators=[telefono_validator],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 912345678',
            'maxlength': '9'
        })
    )

    class Meta:
        model = Cliente
        fields = ['nombres_cli', 'apellidos_cli', 'email_cli', 'numero_cli']
        labels = {
            'nombres_cli': 'Nombre/s',
            'apellidos_cli': 'Apellido/s',
            'email_cli': 'Email',
            'numero_cli': 'Número',
        }
        widgets = {
            'nombres_cli': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa tu nombre'
            }),
            'apellidos_cli': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa tu apellido'
            }),
            'email_cli': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@email.com'
            }),
        }

    # Validación de duplicados
    def clean_email_cli(self):
        email = self.cleaned_data.get('email_cli')
        if Cliente.objects.filter(email_cli=email).exists():
            raise forms.ValidationError("Este email ya está registrado")
        return email

    def clean_numero_cli(self):
        numero = self.cleaned_data.get('numero_cli')
        if Cliente.objects.filter(numero_cli=numero).exists():
            raise forms.ValidationError("Este número ya está registrado")
        return numero
