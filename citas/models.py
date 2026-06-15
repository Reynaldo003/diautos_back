# citas/models.py
from django.db import models
from django.core.exceptions import ValidationError
from clientes.models import ClienteComercial


ESTADOS_ORIGINALES = [
    ("Nadie contesta", "Nadie contesta"),
    ("Número incorrecto, contactable por otro medio", "Número incorrecto, contactable por otro medio"),
    ("Número incorrecto, incontactable por otro medio", "Número incorrecto, incontactable por otro medio"),
    ("Cliente falleció", "Cliente falleció"),
    ("Cliente ya no cuenta con la unidad, pasó a un segundo dueño, incontactable", "Cliente ya no cuenta con la unidad, pasó a un segundo dueño, incontactable"),
    ("Cliente no desea ser contactado sólo mensajes informativos", "Cliente no desea ser contactado sólo mensajes informativos"),
    ("Cliente no desea ser contactado", "Cliente no desea ser contactado"),
    ("Cliente tuvo una mala experiencia previa con el distribuidor, no desea ser contactado", "Cliente tuvo una mala experiencia previa con el distribuidor, no desea ser contactado"),
    ("Unidad fue pérdida total o robo", "Unidad fue pérdida total o robo"),
    ("Llamada de cortesía (Presentación equipo Posventa 15 días después de la venta)", "Llamada de cortesía (Presentación equipo Posventa 15 días después de la venta)"),
    ("Contacto informativo", "Contacto informativo"),
    ("Cliente ya realizó su servicio en otro Distribuidor GM", "Cliente ya realizó su servicio en otro Distribuidor GM"),
    ("Cliente ya realizó su servicio en otro taller que no es GM", "Cliente ya realizó su servicio en otro taller que no es GM"),
    ("Cliente tuvo una mala experiencia previa con el distribuidor, requiere acción por parte del distribuidor", "Cliente tuvo una mala experiencia previa con el distribuidor, requiere acción por parte del distribuidor"),
    ("Cliente rechaza invitación a servicio debido a que considera que no le corresponde porque aún no alcanza el tiempo o Kilometraje", "Cliente rechaza invitación a servicio debido a que considera que no le corresponde porque aún no alcanza el tiempo o Kilometraje"),
    ("Cliente rechaza invitación a servicio debido a precio", "Cliente rechaza invitación a servicio debido a precio"),
    ("Cliente rechaza invitación a servicio debido a falta de tiempo", "Cliente rechaza invitación a servicio debido a falta de tiempo"),
    ("Cliente rechaza invitación a servicio debido a otro motivo", "Cliente rechaza invitación a servicio debido a otro motivo"),
    ("Cliente rechaza invitación a servicio debido a que se encuentra fuera del PMA pero puede regresar", "Cliente rechaza invitación a servicio debido a que se encuentra fuera del PMA pero puede regresar"),
    ("Cliente rechaza invitación a servicio debido a que se encuentra fuera del PMA y no va a regresar", "Cliente rechaza invitación a servicio debido a que se encuentra fuera del PMA y no va a regresar"),
    ("Cliente contactado e interesado, en seguimiento", "Cliente contactado e interesado, en seguimiento"),
    ("Cliente contactado e interesado, él regresará la llamada", "Cliente contactado e interesado, él regresará la llamada"),
    ("Otro", "Otro"),
    ("Cliente solicita agendar cita Proactiva", "Cliente solicita agendar cita Proactiva"),
    ("Cliente solicita agendar cita Reactiva", "Cliente solicita agendar cita Reactiva"),
    ("Confirmación de Datos de Cita", "Confirmación de Datos de Cita"),
    ("Recordatorio de Cita (Recordatorio)", "Recordatorio de Cita (Recordatorio)"),
    ("Cliente solicita/aprueba reagendar cita", "Cliente solicita/aprueba reagendar cita"),
    ("Cliente solicita cancelar cita", "Cliente solicita cancelar cita"),
    ("Cliente No Show, intento de reagendamiento sin contacto", "Cliente No Show, intento de reagendamiento sin contacto"),
    ("Cliente No Show, intento de reagendamiento – Cliente atendió pero no dio una fecha de re agendamiento", "Cliente No Show, intento de reagendamiento – Cliente atendió pero no dio una fecha de re agendamiento"),
    ("Aviso unidad terminada", "Aviso unidad terminada"),
    ("Llamada del 3er día (Evaluación de experiencia del cliente)", "Llamada del 3er día (Evaluación de experiencia del cliente)"),
    ("Llamada para seguimiento de unidad en taller", "Llamada para seguimiento de unidad en taller"),
]


ESTADOS_NUEVOS = [
    ("Cliente sin contacto", "Cliente sin contacto"),
    ("Cliente Incontactable", "Cliente Incontactable"),
    ("Cliente no desea ser contactado para Mensaje informativo pero si Prospección", "Cliente no desea ser contactado para Mensaje informativo pero si Prospección"),
    ("Cliente Contactado, Informativo", "Cliente Contactado, Informativo"),
    ("Cliente Contactado, Servicio Rechazado", "Cliente Contactado, Servicio Rechazado"),
    ("Cliente Contactado, en seguimiento", "Cliente Contactado, en seguimiento"),
    ("Cliente Contactado con Cita Agendada", "Cliente Contactado con Cita Agendada"),
    ("Cliente Contactado, Cita Cancelada", "Cliente Contactado, Cita Cancelada"),
    ("Cliente No Show", "Cliente No Show"),
    ("Cliente Contactado, Cita Efectiva", "Cliente Contactado, Cita Efectiva"),
]


ESTADOS_GESTION_CHOICES = ESTADOS_ORIGINALES + ESTADOS_NUEVOS


class Cita(models.Model):
    cliente = models.ForeignKey(
        ClienteComercial,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="citas",
    )
    agencia = models.CharField(max_length=120, blank=True, default="", db_index=True)
    auto_interes = models.CharField(max_length=255, blank=True, default="")
    fecha_hora_cita = models.DateTimeField(null=True, blank=True, db_index=True)
    asistencia = models.BooleanField(default=False, db_index=True)
    tipo_cita = models.CharField(max_length=120, blank=True, default="", db_index=True)
    fuente_prospeccion = models.CharField(max_length=120, blank=True, default="")
    asesor_digital = models.CharField(max_length=200, blank=True, default="")
    asesor_piso = models.CharField(max_length=200, blank=True, default="")
    
   
    estado_gestion = models.CharField(
        max_length=255,
        choices=ESTADOS_GESTION_CHOICES,
        blank=True,
        default="",
        db_index=True
    )
    
    
    detalle_gestion = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Detalle de gestión",
        help_text="Campo dinámico que aparece según el estado seleccionado (cita, motivo, seguimiento, etc.)"
    )
    
    comentarios = models.CharField(max_length=2000, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "citas"
        managed = True
        indexes = [
            models.Index(fields=["agencia", "fecha_hora_cita"], name="idx_cita_agencia_fecha"),
            models.Index(fields=["estado_gestion"], name="idx_cita_estado_gestion"),
        ]

    def __str__(self):
        return f"Cita #{self.id} - {self.cliente.telefono}"