from django.db import models

from retencion.models import OrdenServicioVentaDiautos
from usuarios.models import Usuario


class CarteraCliente(models.Model):
    """
    NOTA: Se eliminaron los choices fijos de EstadoGestion porque el frontend
    maneja tipificaciones largas como "Cliente solicita agendar cita Proactiva",
    "Nadie contesta", etc. que no caben en los choices originales.
    El campo ahora es texto libre con max_length=255.
    Se agregó detalle_gestion para el "Estatus del perfil" que se autocompleta
    en el frontend según la tipificación elegida.
    """

    id = models.BigAutoField(primary_key=True)

    venta = models.ForeignKey(
        OrdenServicioVentaDiautos,
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="asignaciones_cartera",
        db_constraint=False,
    )

    vin = models.CharField(max_length=150, db_index=True)
    vin_normalizado = models.CharField(max_length=150, unique=True, db_index=True)

    nombre_cliente = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    celular = models.CharField(max_length=30, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)

    marca_vehiculo = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    version = models.CharField(max_length=150, null=True, blank=True)
    ano_modelo = models.SmallIntegerField(null=True, blank=True)

    fecha_venta = models.DateField(null=True, blank=True, db_index=True)
    folio_factura = models.CharField(max_length=50, null=True, blank=True)
    vendedor = models.CharField(max_length=150, null=True, blank=True)

    fecha_os = models.DateField(null=True, blank=True)
    id_os = models.CharField(max_length=50, null=True, blank=True)
    asesor_servicio = models.CharField(max_length=255, null=True, blank=True)
    estado_cliente = models.CharField(max_length=20, null=True, blank=True)
    dias_os_a_actual = models.IntegerField(null=True, blank=True)
    meses_actual_a_venta = models.IntegerField(null=True, blank=True)
    franja_retencion = models.CharField(max_length=50, null=True, blank=True)
    prioridad_prospeccion = models.CharField(max_length=50, null=True, blank=True)
    kilometraje = models.CharField(max_length=50, null=True, blank=True)

    asesor_asignado = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="cartera_clientes_asignados",
    )

    # ── Gestión BDC ───────────────────────────────────────────────────────────
    # estado_gestion: tipificación de actividad (texto libre, valores definidos
    # en el frontend en ESTADOS_GESTION).
    # Ejemplos: "Nadie contesta", "Cliente solicita agendar cita Proactiva", etc.
    estado_gestion = models.CharField(
        max_length=255,
        default="PENDIENTE",
        blank=True,
        db_index=True,
    )

    # detalle_gestion: estatus del perfil del cliente, se autocompleta según
    # el mapeo MAPEO_ESTADO_A_DETALLE del frontend.
    # Ejemplos: "Cliente sin contacto", "Cliente Contactado con Cita Agendada", etc.
    detalle_gestion = models.TextField(
        blank=True,
        default="",
    )
    # ─────────────────────────────────────────────────────────────────────────

    asignado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    creado_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="carteras_creadas",
    )

    origen = models.CharField(max_length=30, default="AUTOMATICO")
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "cartera_clientes"
        managed = True
        ordering = ["-asignado_en", "-id"]
        indexes = [
            models.Index(fields=["asesor_asignado", "estado_gestion"]),
            models.Index(fields=["fecha_venta"]),
            models.Index(fields=["ano_modelo", "modelo"]),
            models.Index(fields=["meses_actual_a_venta"]),
            models.Index(fields=["asignado_en"]),
            models.Index(
                fields=["activo", "vin_normalizado"],
                name="idx_cartera_activo_vin",
            ),
        ]

    def save(self, *args, **kwargs):
        self.vin = str(self.vin or "").strip().upper()
        self.vin_normalizado = self.vin
        self.modelo = obtener_modelo_desde_version(self.version)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vin} - {self.nombre_cliente or 'Cliente'} - {self.asesor_asignado}"


def obtener_modelo_desde_version(version):
    texto = str(version or "").strip()
    if not texto:
        return "SIN MODELO"

    return (
        texto.replace(",", " ")
        .replace(".", " ")
        .split()[0]
        .strip()
        .upper()
    )