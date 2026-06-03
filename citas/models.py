# citas/models.py
from django.db import models
from django.core.exceptions import ValidationError
from clientes.models import ClienteComercial

class Cita(models.Model):
    cliente = models.ForeignKey(
        ClienteComercial,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="citas",
    )

    agencia = models.CharField(max_length=120, blank=True, default="")
    auto_interes = models.CharField(max_length=255, blank=True, default="")
    fecha_hora_cita = models.DateTimeField(null=True, blank=True)
    asistencia = models.BooleanField(default=False)

    tipo_cita = models.CharField(max_length=120, blank=True, default="")
    fuente_prospeccion = models.CharField(max_length=120, blank=True, default="")
    asesor_digital = models.CharField(max_length=200, blank=True, default="")
    asesor_piso = models.CharField(max_length=200, blank=True, default="")
    comentarios = models.CharField(max_length=2000, blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "citas"
        managed = True

    def __str__(self):
        return f"Cita #{self.id} - {self.cliente.telefono}"
