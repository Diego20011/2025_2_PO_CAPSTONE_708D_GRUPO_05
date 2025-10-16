# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Sesion(models.Model):
    id_sesion = models.AutoField(primary_key=True)
    asiste = models.IntegerField()
    comentarios_ses = models.TextField(blank=True, null=True)
    hora_inicio_ses = models.TimeField(blank=True, null=True)
    hora_termino_ses = models.TimeField(blank=True, null=True)
    canino_id_canino = models.ForeignKey('reservas.Canino', on_delete=models.PROTECT, db_column='canino_id_canino')
    reserva_id_reserva = models.ForeignKey('reservas.Reserva', on_delete=models.PROTECT, db_column='reserva_id_reserva')

    class Meta:
        managed = False
        db_table = 'sesion'
