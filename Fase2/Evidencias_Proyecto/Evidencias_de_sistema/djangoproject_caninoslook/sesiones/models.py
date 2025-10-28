from django.db import models


class Sesion(models.Model):
    id_sesion = models.AutoField(primary_key=True)
    asiste = models.BooleanField("Asiste")
    cont_aviso_retiro_ses = models.PositiveIntegerField("Contador de avisos para retiro.")
    conf_aviso_retiro_ses = models.BooleanField("Confirmación recibo de aviso para retiro")
    comentarios_ses = models.TextField("Comentarios", blank=True, null=True)
    hora_inicio_ses = models.TimeField("Hora inicio sesión", blank=True, null=True)
    hora_termino_ses = models.TimeField("Hora termino sesión", blank=True, null=True)
    canino_id_ses = models.ForeignKey(
        'reservas.Canino',
        verbose_name="Canino",
        on_delete=models.PROTECT,
        db_column='canino_id_ses',
        related_name='sesiones')
    reserva_id_ses = models.OneToOneField(
        'reservas.Reserva',
        verbose_name="Reserva",
        unique=True, 
        on_delete=models.PROTECT, 
        db_column='reserva_id_ses', 
        related_name='reservas')

    class Meta:
        db_table = 'sesion' #Esto le dice a Django el nombre exacto de la tabla que debe usar en la base de datos. por defecto guarda: nombreApp_nombreTabla
        verbose_name = "Sesion" #Es el nombre legible en singular que se muestra en el panel de administración de Django (admin) y en formularios.
        verbose_name_plural = "Sesiones" #Similar al verbose_name, pero en plural, también usado en el admin y otras interfaces.
