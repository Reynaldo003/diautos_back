from django.db import models

class UnidadesVendidas(models.Model):
    id = models.BigAutoField(primary_key=True)

    tipo = models.CharField(max_length=255, null=True, blank=True, db_column="tipo")
    tipo_de_venta = models.CharField(max_length=30, null=True, blank=True, db_column="tipo_de_venta")
    VIN = models.CharField(max_length=60, null=True, blank=True, db_column="VIM")
    año = models.CharField(max_length=10, null=True, blank=True, db_column="año")
    modelo = models.CharField(max_length=100, null=True, blank=True, db_column="modelo")
    ciudad = models.CharField(max_length=100, null=True, blank=True, db_column="ciudad")
    estado = models.CharField(max_length=100, null=True, blank=True, db_column="estado")

    codigo_postal = models.CharField(max_length=10, null=True, blank=True, db_column="codigo_postal")
    km_distribuidor = models.CharField(max_length=10, null=True, blank=True, db_column="km_distribuidor")
    ult_fecha_OS_en_distribuidora = models.DateField(null=True, blank=True, db_column="ult_fecha_OS_en_distribuidora")
    meses_ult_OS = models.IntegerField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="meses_ult_OS")
    ult_lectura_odometro = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ult_lectura_odometro")
    PMA = models.BooleanField(blank=True,default=False, db_column="PMA")
    vendido_distribuidor = models.BooleanField(blank=True,default=False, db_column="PMA")
    atendido_OS_distribuidor = models.BooleanField(blank=True,default=False, db_column="PMA")
    primera_fecha_venta = models.DateField(null=True, blank=True, db_column="ult_fecha_OS")
    ultima_fecha_compra = models.DateField(null=True, blank=True, db_column="ult_fecha_OS")
    meses_desde_venta = models.IntegerField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="meses_ult_OS")
    ult_fecha_OS_otra_distribuidora = models.DateField(null=True, blank=True, db_column="ult_fecha_OS_otra_distribuidora")
    no_distribuidor = models.IntegerField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="meses_ult_OS")
    meses_ult_OS = models.IntegerField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="meses_ult_OS")
    meses_ult_OS = models.IntegerField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="meses_ult_OS")

    class Meta:
        db_table = "Ordenes_Servicio_Ventas_DIAUTOS"
        managed = False
        ordering = ["-id"]

    def __str__(self):
        return f"{self.id} - {self.nombre_cte}"
