from django.db import models


class OrdenServicioVentaDiautos(models.Model):
    id = models.BigAutoField(primary_key=True)

    nombre_cte = models.CharField(max_length=255, null=True, blank=True, db_column="Nombre_CTE")
    telefono = models.CharField(max_length=30, null=True, blank=True, db_column="Telefono")
    celular = models.CharField(max_length=30, null=True, blank=True, db_column="Celular")
    email = models.CharField(max_length=255, null=True, blank=True, db_column="Email")
    marca_vehiculo = models.CharField(max_length=100, null=True, blank=True, db_column="Marca_Vehiculo")
    version = models.CharField(max_length=100, null=True, blank=True, db_column="Version")
    ano_modelo = models.SmallIntegerField(null=True, blank=True, db_column="Año_Modelo")
    numero_serie = models.CharField(max_length=150, null=True, blank=True, db_column="Numero_Serie")
    importe_factura = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="Importe_Factura")
    importe_costo_base = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="Importe_Costo_Base")
    importe_iva = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ImporteIVA")
    importe_isan = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ImporteISAN")
    importe_bonificacion = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ImporteBonificacion")

    tipo_movimiento = models.CharField(max_length=30, null=True, blank=True, db_column="TipoMovimiento")
    vendedor = models.CharField(max_length=150, null=True, blank=True, db_column="Vendedor")
    fecha_venta = models.DateField(null=True, blank=True, db_column="Fecha_Venta")
    folio_factura = models.CharField(max_length=50, null=True, blank=True, db_column="Folio_Factura")
    condicion_pago = models.CharField(max_length=50, null=True, blank=True, db_column="CondicionPago")

    fecha_os = models.DateField(null=True, blank=True, db_column="Fecha_OS")
    id_os = models.CharField(max_length=50, null=True, blank=True, db_column="ID_OS")
    tipo_orden_servicio = models.CharField(max_length=50, null=True, blank=True, db_column="Tipo_Orden_Servicio")
    asesor = models.CharField(max_length=255, null=True, blank=True, db_column="Asesor")
    transaccion = models.CharField(max_length=100, null=True, blank=True, db_column="Transaccion")
    clasificacion = models.CharField(max_length=150, null=True, blank=True, db_column="Clasificacion")
    estado_os = models.CharField(max_length=100, null=True, blank=True, db_column="Estado_OS")
    descripcion_os = models.CharField(max_length=1000, null=True, blank=True, db_column="Descripcion_OS")
    costo_os = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="Costo_OS")
    condicion_vehiculo = models.CharField(max_length=20, null=True, blank=True, db_column="Condicion_Vehiculo")
    estado_cliente = models.CharField(max_length=20, null=True, blank=True, db_column="Estado_Cliente")
    dias_os_a_actual = models.IntegerField(null=True, blank=True, db_column="Dias_OS_A_Actual")
    prioridad_prospeccion = models.CharField(max_length=50, null=True, blank=True, db_column="Prioridad_Prospeccion")
    franja_retencion = models.CharField(max_length=50, null=True, blank=True, db_column="Franja_Retencion")
    meses_actual_a_venta = models.IntegerField(null=True, blank=True, db_column="Meses_Actual_A_Venta")
    kilometraje = models.CharField(max_length=50, null=True, blank=True, db_column="kilometraje")

    class Meta:
        db_table = "Ordenes_Servicio_Ventas_DIAUTOS"
        managed = False
        ordering = ["-id"]

    def __str__(self):
        return f"{self.id} - {self.nombre_cte}"


class DetalleVentasPostVentaLimpia(models.Model):
    ord_tiempotab = models.FloatField(null=True, blank=True, db_column="ord_tiempotab")
    ore_idorden = models.CharField(max_length=50, primary_key=True, db_column="ORE_IDORDEN")

    per_telcelular = models.CharField(max_length=30, null=True, blank=True, db_column="PER_TELCELULAR")
    veh_contacto = models.CharField(max_length=150, null=True, blank=True, db_column="VEH_CONTACTO")
    tel_contacto = models.CharField(max_length=30, null=True, blank=True, db_column="TEL_CONTACTO")
    ore_idcliente = models.CharField(max_length=50, null=True, blank=True, db_column="ORE_IDCLIENTE")
    nombre_cte = models.CharField(max_length=255, null=True, blank=True, db_column="NOMBRE_CTE")
    ore_idclifac = models.CharField(max_length=50, null=True, blank=True, db_column="ORE_IDCLIFAC")
    nombre_ctefac = models.CharField(max_length=255, null=True, blank=True, db_column="NOMBRE_CTEFAC")
    ore_fechaprom = models.DateField(null=True, blank=True, db_column="ORE_FECHAPROM")
    ore_fechacie = models.DateField(null=True, blank=True, db_column="ORE_FECHACIE")
    fpago = models.CharField(max_length=100, null=True, blank=True, db_column="FPAGO")
    tiporden = models.CharField(max_length=100, null=True, blank=True, db_column="TIPORDEN")
    ore_status = models.CharField(max_length=100, null=True, blank=True, db_column="ORE_STATUS")
    nombre = models.CharField(max_length=255, null=True, blank=True, db_column="NOMBRE")
    ore_numserie = models.CharField(max_length=100, null=True, blank=True, db_column="ORE_NUMSERIE")
    ore_fechaord = models.DateField(null=True, blank=True, db_column="ORE_FECHAORD")
    cono = models.CharField(max_length=100, null=True, blank=True, db_column="CONO")
    asesor = models.CharField(max_length=255, null=True, blank=True, db_column="ASESOR")
    per_lada = models.CharField(max_length=10, null=True, blank=True, db_column="PER_LADA")
    per_telefono1 = models.CharField(max_length=30, null=True, blank=True, db_column="PER_TELEFONO1")
    per_telefono2 = models.CharField(max_length=30, null=True, blank=True, db_column="PER_TELEFONO2")
    status = models.CharField(max_length=100, null=True, blank=True, db_column="STATUS")
    vte_horadocto = models.CharField(max_length=30, null=True, blank=True, db_column="VTE_HORADOCTO")
    colointerior = models.CharField(max_length=100, null=True, blank=True, db_column="COLOINTERIOR")
    veh_tipoauto = models.CharField(max_length=100, null=True, blank=True, db_column="VEH_TIPOAUTO")
    colorexterior = models.CharField(max_length=100, null=True, blank=True, db_column="COLOREXTERIOR")
    ord_subtotal = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ORD_SUBTOTAL")
    ord_costo = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column="ORD_COSTO")
    veh_noplacas = models.CharField(max_length=30, null=True, blank=True, db_column="VEH_NOPLACAS")
    veh_anmodelo = models.CharField(max_length=30, null=True, blank=True, db_column="VEH_ANMODELO")
    noplacaskod = models.CharField(max_length=30, null=True, blank=True, db_column="NOPLACASKOD")
    colextkod = models.CharField(max_length=500, null=True, blank=True, db_column="COLEXTKOD")
    colintkod = models.CharField(max_length=500, null=True, blank=True, db_column="COLINTKOD")
    dias_hasta_hoy = models.FloatField(null=True, blank=True, db_column="DiasHastaHoy")
    aseguradora = models.CharField(max_length=255, null=True, blank=True, db_column="ASEGURADORA")
    vte_fechdocto = models.DateField(null=True, blank=True, db_column="VTE_FECHDOCTO")
    factura = models.CharField(max_length=100, null=True, blank=True, db_column="FACTURA")
    fecha_factura = models.DateField(null=True, blank=True, db_column="FECHA_FACTURA")
    ore_idpoliza = models.CharField(max_length=100, null=True, blank=True, db_column="ORE_IDPOLIZA")
    ore_idsiniestro = models.CharField(max_length=100, null=True, blank=True, db_column="ORE_IDSINIESTRO")
    per_rfc = models.CharField(max_length=30, null=True, blank=True, db_column="PER_RFC")
    per_email = models.CharField(max_length=255, null=True, blank=True, db_column="PER_EMAIL")
    per_calle1 = models.CharField(max_length=255, null=True, blank=True, db_column="PER_CALLE1")
    per_ciudad = models.CharField(max_length=150, null=True, blank=True, db_column="PER_CIUDAD")
    per_delegac = models.CharField(max_length=150, null=True, blank=True, db_column="PER_DELEGAC")
    per_numexter = models.CharField(max_length=30, null=True, blank=True, db_column="PER_NUMEXTER")
    per_numiner = models.CharField(max_length=30, null=True, blank=True, db_column="PER_NUMINER")
    per_codpos = models.CharField(max_length=20, null=True, blank=True, db_column="PER_CODPOS")
    ore_kilometraje = models.CharField(max_length=50, null=True, blank=True, db_column="ORE_KILOMETRAJE")
    ore_observaciones = models.TextField(null=True, blank=True, db_column="ORE_OBSERVACIONES")
    orden = models.CharField(max_length=50, null=True, blank=True, db_column="ORDEN")
    clasificacion = models.CharField(max_length=150, null=True, blank=True, db_column="clasificacion")
    ore_idcita = models.CharField(max_length=50, null=True, blank=True, db_column="ore_idcita")
    sal_fecsalida = models.CharField(max_length=30, null=True, blank=True, db_column="sal_fecsalida")
    sal_horasalida = models.CharField(max_length=30, null=True, blank=True, db_column="sal_horasalida")
    sal_idsalida = models.CharField(max_length=50, null=True, blank=True, db_column="sal_idsalida")
    ord_status = models.CharField(max_length=100, null=True, blank=True, db_column="ORD_STATUS")
    desc_auto = models.CharField(max_length=255, null=True, blank=True, db_column="DESC_AUTO")
    ord_descrip = models.CharField(max_length=1000, null=True, blank=True, db_column="ORD_DESCRIP")
    ord_referencia2 = models.CharField(max_length=255, null=True, blank=True, db_column="ORD_REFERENCIA2")
    tecnico = models.CharField(max_length=255, null=True, blank=True, db_column="TECNICO")
    situacion = models.CharField(max_length=100, null=True, blank=True, db_column="situacion")
    nivelasegurado = models.CharField(max_length=100, null=True, blank=True, db_column="NIVELASEGURADO")
    email_contacto = models.CharField(max_length=255, null=True, blank=True, db_column="EMAIL_CONTACTO")
    contacto_celular = models.CharField(max_length=30, null=True, blank=True, db_column="CONTACTO_CELULAR")
    conductor_nombre = models.CharField(max_length=255, null=True, blank=True, db_column="CONDUCTOR_NOMBRE")
    conductor_telefono = models.CharField(max_length=30, null=True, blank=True, db_column="CONDUCTOR_TELEFONO")
    conductor_celular = models.CharField(max_length=30, null=True, blank=True, db_column="CONDUCTOR_CELULAR")

    class Meta:
        db_table = "detalle_ventas_PostVenta_limpia"
        managed = False
        ordering = ["-ore_fechaord", "-ore_fechacie", "-vte_fechdocto"]

    def __str__(self):
        return f"{self.ore_idorden} - {self.ore_numserie}"