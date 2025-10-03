from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['id_cliente', 'nombres_cli', 'apellidos_cli', 'email_cli', 'numero_cli']
        labels = {
            'nombres_cli': 'Nombre/s',
            'apellidos_cli': 'Apellido/s',
            'email_cli': 'Email',
            'numero_cli': 'Número',
        }