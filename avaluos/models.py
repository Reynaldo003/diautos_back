#avaluos/models.py
from pathlib import Path
import uuid

from django.db import models
from clientes.models import ClienteComercial


def avaluo_evidencia_upload_to(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"avaluos/evidencias/{instance.avaluo_id}/{uuid.uuid4().hex}{ext}"


class AvaluoUsado(models.Model):
    TIPO_VALUACION_VALUACION = "valuacion"
    TIPO_VALUACION_FRESH_UP = "fresh_up"
    TIPO_VALUACION_SERVICIO = "valuacion_servicio"
    TIPO_VALUACION_BDC = "valuacion_bdc"

    TIPO_VALUACION_CHOICES = (
        (TIPO_VALUACION_VALUACION, "Valuación"),
        (TIPO_VALUACION_FRESH_UP, "Fresh Up"),
        (TIPO_VALUACION_SERVICIO, "Valuación de servicio"),
        (TIPO_VALUACION_BDC, "Valuación de BDC"),
    )

    TIPO_TOMA_SERVICIO = "de_servicio"
    TIPO_TOMA_CANAL = "canal"

    TIPO_TOMA_CHOICES = (
        (TIPO_TOMA_SERVICIO, "De servicio"),
        (TIPO_TOMA_CANAL, "Canal"),
    )

    cliente = models.ForeignKey(
        ClienteComercial,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="avaluos_usados",
    )

    agencia = models.CharField(max_length=120, default="", null=True, blank=True)
    fecha_avaluo = models.DateTimeField(null=True, blank=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    fecha_toma_cuenta = models.DateTimeField(null=True, blank=True)
    agenda_valuacion = models.DateTimeField(null=True, blank=True)

    asesor_ventas = models.CharField(max_length=200, default="", null=True, blank=True)
    vendedor = models.CharField(max_length=200, default="", null=True, blank=True)

    tipo_valuacion = models.CharField(
        max_length=40,
        choices=TIPO_VALUACION_CHOICES,
        default=TIPO_VALUACION_VALUACION,
        null=True,
        blank=True,
    )

    tipo_toma = models.CharField(
        max_length=40,
        choices=TIPO_TOMA_CHOICES,
        default="",
        null=True,
        blank=True,
    )

    marca_auto = models.CharField(max_length=120, default="", null=True, blank=True)
    modelo = models.CharField(max_length=120, default="", null=True, blank=True)
    anio_modelo = models.CharField(max_length=10, default="", null=True, blank=True)
    version = models.CharField(max_length=120, default="", null=True, blank=True)
    serie = models.CharField(max_length=120, default="", null=True, blank=True)
    placas = models.CharField(max_length=40, default="", null=True, blank=True)
    kilometraje = models.CharField(max_length=50, default="", null=True, blank=True)
    color = models.CharField(max_length=120, default="", null=True, blank=True)

    precio_guia = models.CharField(max_length=120, default="", null=True, blank=True)
    precio_compra_libro_azul = models.CharField(max_length=120, default="", null=True, blank=True)
    precio_venta_libro_azul = models.CharField(max_length=120, default="", null=True, blank=True)

    costo_reparacion = models.CharField(max_length=120, default="0.00", null=True, blank=True)
    costo_estimado = models.CharField(max_length=120, default="", null=True, blank=True)
    costo_mecanica_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    oferta_inicial = models.CharField(max_length=120, default="", null=True, blank=True)
    oferta_final = models.CharField(max_length=120, default="", null=True, blank=True)

    origen_valuacion = models.CharField(max_length=120, default="", null=True, blank=True)
    descripcion = models.TextField(max_length=4000, default="", null=True, blank=True)
    observaciones = models.TextField(max_length=4000, default="", null=True, blank=True)
    comentarios = models.TextField(max_length=4000, default="Valuación", null=True, blank=True)
    comentarios_checklist = models.TextField(
        max_length=4000,
        default="",
        null=True,
        blank=True,
    )
    ganador_subasta = models.CharField(max_length=200, default="", null=True, blank=True)
    etapa_proceso = models.CharField(max_length=200, default="", null=True, blank=True)

    checklist_100 = models.JSONField(default=dict, blank=True)

    tecnico_finalizado = models.BooleanField(default=False)
    fecha_tecnico_finalizado = models.DateTimeField(null=True, blank=True)

    valuacion_terminada = models.BooleanField(default=False)
    fecha_valuacion_terminada = models.DateTimeField(null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "avaluos"
        managed = True
        ordering = ["-creado"]

    def __str__(self):
        nombre = self.cliente.nombre or "Cliente"
        telefono = self.cliente.telefono or "Sin teléfono"
        vehiculo = f"{self.marca_auto or ''} {self.modelo or ''}".strip()
        return f"{nombre} - {vehiculo} - {telefono}".strip()


class AvaluoUsadoEvidencia(models.Model):
    TIPO_IMAGEN = "imagen"
    TIPO_VIDEO = "video"
    TIPO_ARCHIVO = "archivo"

    TIPOS = (
        (TIPO_IMAGEN, "Imagen"),
        (TIPO_VIDEO, "Video"),
        (TIPO_ARCHIVO, "Archivo"),
    )

    CATEGORIA_ESTETICO = "estetico"
    CATEGORIA_MECANICO = "mecanico"
    CATEGORIA_HYP = "hyp"

    CATEGORIAS = (
        (CATEGORIA_ESTETICO, "Estético"),
        (CATEGORIA_MECANICO, "Mecánico"),
        (CATEGORIA_HYP, "HYP"),
    )

    avaluo = models.ForeignKey(
        AvaluoUsado,
        db_column="id_avaluo",
        on_delete=models.CASCADE,
        related_name="evidencias",
    )
    archivo = models.FileField(upload_to=avaluo_evidencia_upload_to)
    nombre = models.CharField(max_length=255, default="", blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_ARCHIVO)

    categoria_concepto = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default=CATEGORIA_ESTETICO,
    )
    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=500, default="", blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "avaluos_evidencias"
        managed = True
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre or f"Evidencia {self.pk}"


class ConceptoAvaluo(models.Model):
    TIPO_MECANICO = "mecanico"
    TIPO_ESTETICO = "estetico"
    TIPO_HYP = "hyp"

    TIPOS_CONCEPTO = (
        (TIPO_MECANICO, "Mecánico"),
        (TIPO_ESTETICO, "Estético"),
        (TIPO_HYP, "HYP"),
    )

    avaluo = models.ForeignKey(
        AvaluoUsado,
        db_column="id_avaluo",
        on_delete=models.CASCADE,
        related_name="conceptos",
    )
    descripcion = models.TextField(max_length=4000, default="", blank=True)
    tipo_concepto = models.CharField(
        max_length=20,
        choices=TIPOS_CONCEPTO,
        default=TIPO_MECANICO,
    )
    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conceptos_avaluos"
        managed = True
        ordering = ["id"]

    def __str__(self):
        return self.descripcion or f"Concepto {self.pk}"