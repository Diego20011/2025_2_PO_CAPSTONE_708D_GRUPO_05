from django.db import models

# En los modelos solo puedes usar cosas como max_length, blank, null, unique, default y validators.

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombres_cli = models.CharField("Nombre/s", max_length=30, blank=False)
    apellidos_cli = models.CharField("Apellido/s", max_length=30, blank=False)
    email_cli = models.EmailField("Correo electrónico", max_length=70, unique=True, blank=False)
    numero_cli = models.CharField("Número de contacto", max_length=12, blank=False)
    password = models.CharField("Contraseña", max_length=128, blank=False)

    class Meta:
        db_table = 'cliente'
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.nombres_cli} {self.apellidos_cli}"


class Canino(models.Model):
    # Opciones para tamaño
    tamaño_choices = [
        ("", "Seleccione tamaño"),
        ("Pequeño", "Pequeño"),
        ("Mediano", "Mediano"),
        ("Grande", "Grande")
    ]

    id_canino = models.AutoField(primary_key=True)
    nombre_can = models.CharField("Nombre", max_length=20)
    fecha_nac_can = models.DateField("Fecha de nacimiento")
    raza_can = models.CharField("Raza", max_length=15)
    peso_can = models.PositiveIntegerField("Peso (kg)")
    tamano_can = models.CharField("Tamaño", max_length=10, choices=tamaño_choices)
    cuidados_esp_can = models.TextField("Cuidados especiales", blank=True, null=True)
    cliente_id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column='cliente_id_cliente',
        related_name='caninos'
    )

    class Meta:
        db_table = 'canino'
        verbose_name = "Canino"
        verbose_name_plural = "Caninos"

    def __str__(self):
        return self.nombre_can


class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    servicio_res = models.CharField("Servicio", max_length=20)
    hora_res = models.TimeField("Hora")
    fecha_res = models.DateField("Fecha")
    medio_pago_res = models.CharField("Medio de pago", max_length=15)
    valor_res = models.PositiveIntegerField("Valor")
    confirm_pago_res = models.BooleanField("Pago confirmado", default=False)
    cliente_id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column='cliente_id_cliente',
        related_name='reservas'
    )
    canino_id_canino = models.ForeignKey(
        Canino,
        on_delete=models.PROTECT,
        db_column='canino_id_canino',
        related_name='reservas'
    )

    class Meta:
        db_table = 'reserva'
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

    def __str__(self):
        return f"{self.servicio_res} - {self.fecha_res} {self.hora_res}"
