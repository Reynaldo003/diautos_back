#encuestas/models.py
from django.db import models

class EncuestaServicio(models.Model):
    id_encuesta = models.AutoField(primary_key=True)
    creado = models.DateTimeField(auto_now_add=True)
    numero_OS = models.CharField(max_length=200, blank=True, default="")
    asesor = models.CharField(max_length=200, blank=True, default="")
    satisfaccion_agendar_cita = models.IntegerField(blank=True, default=0)
    satisfaccion_exp_area_servicio = models.IntegerField(blank=True, default=0)
    mostraron_inventario_inicial_vehiculo = models.BooleanField(default=False)
    explicacion_clara_trabajo_realizado = models.BooleanField(default=False)
    invitacion_realizar_inventario = models.BooleanField(default=False)
    entrego_reporte_multipuntos = models.BooleanField(default=False)
    trabajo_realizado_cumple_espectativa = models.BooleanField(default=False)
    comentario = models.CharField(max_length=1000, blank=True, null=True, default="")

    class Meta:
        db_table = "encuestas_servicio"
        managed = True
