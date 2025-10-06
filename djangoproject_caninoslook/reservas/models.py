# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    servicio_res = models.CharField(max_length=20)
    hora_res = models.TimeField()
    fecha_res = models.DateField()
    medio_pago_res = models.CharField(max_length=15)
    valor_res = models.IntegerField()
    confirm_pago_res = models.IntegerField()
    canino_id_canino = models.ForeignKey('Canino', on_delete=models.PROTECT, db_column='canino_id_canino')
    cliente_id_cliente = models.ForeignKey('Cliente', on_delete=models.PROTECT, db_column='cliente_id_cliente')
    sesion_id_sesion = models.ForeignKey('sesiones.Sesion', on_delete=models.PROTECT, db_column='sesion_id_sesion')

    class Meta:
        managed = False
        db_table = 'reserva'


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombres_cli = models.CharField(max_length=30)
    apellidos_cli = models.CharField(max_length=30)
    email_cli = models.CharField(max_length=70)
    numero_cli = models.IntegerField()
    password      = models.CharField(max_length=128)

    class Meta:
        managed = False
        db_table = 'cliente'


class Canino(models.Model):
    id_canino = models.AutoField(primary_key=True)
    nombre_can = models.CharField(max_length=20)
    edad_can = models.IntegerField()
    raza_can = models.CharField(max_length=15)
    peso_can = models.IntegerField()
    tamano_can = models.CharField(max_length=10)
    cuidados_esp_can = models.TextField(blank=True, null=True)
    cliente_id_cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, db_column='cliente_id_cliente')

    class Meta:
        managed = False
        db_table = 'canino'
