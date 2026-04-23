from collections import defaultdict
import re
from datetime import date, datetime

from django.db.models import Q
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DetalleVentasPostVentaLimpia, OrdenServicioVentaDiautos
from .pagination import RetencionPagination
from .serializers import (
    DetalleVentasPostVentaLimpiaSerializer,
    OrdenServicioVentaDiautosSerializer,
)


SERVICIOS_COMERCIALES = [
    {
        "clave": "balatas",
        "nombre": "Balatas",
        "keywords": ["BALATA", "BALATAS", "PASTILLA DE FRENO", "PASTILLAS DE FRENO"],
        "intervalo_dias": 180,
    },
    {
        "clave": "liquido_frenos",
        "nombre": "Líquido de frenos",
        "keywords": ["LIQUIDO DE FRENOS", "LÍQUIDO DE FRENOS", "FLUSH DE FRENOS"],
        "intervalo_dias": 365,
    },
    {
        "clave": "aceite",
        "nombre": "Cambio de aceite",
        "keywords": ["CAMBIO DE ACEITE", "ACEITE", "SERVICIO DE ACEITE"],
        "intervalo_dias": 180,
    },
    {
        "clave": "filtro_aire",
        "nombre": "Filtro de aire",
        "keywords": ["FILTRO DE AIRE"],
        "intervalo_dias": 365,
    },
    {
        "clave": "filtro_polen",
        "nombre": "Filtro de polen",
        "keywords": ["FILTRO DE POLEN", "FILTRO A/C", "FILTRO DE CABINA"],
        "intervalo_dias": 365,
    },
    {
        "clave": "bateria",
        "nombre": "Batería",
        "keywords": ["BATERIA", "BATERÍA"],
        "intervalo_dias": 730,
    },
    {
        "clave": "llantas",
        "nombre": "Llantas",
        "keywords": ["LLANTA", "LLANTAS", "NEUMATICO", "NEUMÁTICO"],
        "intervalo_dias": 730,
    },
    {
        "clave": "amortiguadores",
        "nombre": "Amortiguadores",
        "keywords": ["AMORTIGUADOR", "AMORTIGUADORES"],
        "intervalo_dias": 730,
    },
    {
        "clave": "alineacion_balanceo",
        "nombre": "Alineación y balanceo",
        "keywords": ["ALINEACION", "ALINEACIÓN", "BALANCEO"],
        "intervalo_dias": 180,
    },
]


def obtener_modelo_desde_version(version: str) -> str:
    if not version:
        return "SIN MODELO"

    return (
        str(version)
        .strip()
        .split()[0]
        .replace(",", "")
        .replace(".", "")
        .upper()
    )


def normalizar_texto(*valores):
    texto = " ".join(str(valor or "") for valor in valores)
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extraer_numero_entero(valor):
    if valor in (None, ""):
        return None

    solo_digitos = re.sub(r"[^\d]", "", str(valor))
    if not solo_digitos:
        return None

    try:
        return int(solo_digitos)
    except (TypeError, ValueError):
        return None


def convertir_a_fecha(valor):
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    return None


def obtener_fecha_postventa(item):
    return (
        convertir_a_fecha(item.ore_fechaord)
        or convertir_a_fecha(item.ore_fechacie)
        or convertir_a_fecha(item.vte_fechdocto)
        or convertir_a_fecha(item.fecha_factura)
        or convertir_a_fecha(item.ore_fechaprom)
    )


def obtener_descripcion_postventa(item):
    return (
        item.ord_descrip
        or item.ord_referencia2
        or item.clasificacion
        or item.tiporden
        or item.desc_auto
        or "Sin descripción"
    )


def calcular_estatus_revision(dias_desde, intervalo_dias):
    if dias_desde is None:
        return "Sin fecha"

    if dias_desde >= intervalo_dias:
        return "Revisar ahora"

    if dias_desde >= int(intervalo_dias * 0.75):
        return "Próximo a revisar"

    return "Aún reciente"


def construir_resumen_servicios(historial, kilometraje_actual=None):
    hoy = date.today()
    kilometraje_actual_num = extraer_numero_entero(kilometraje_actual)
    resumen = []

    for servicio in SERVICIOS_COMERCIALES:
        coincidencias = []

        for item in historial:
            texto = normalizar_texto(
                item.ord_descrip,
                item.ord_referencia2,
                item.clasificacion,
                item.tiporden,
                item.desc_auto,
            )

            if any(keyword in texto for keyword in servicio["keywords"]):
                coincidencias.append(item)

        if not coincidencias:
            continue

        coincidencias_ordenadas = sorted(
            coincidencias,
            key=lambda item: (
                obtener_fecha_postventa(item) or date.min,
                str(item.ore_idorden or ""),
            ),
            reverse=True,
        )

        ultimo = coincidencias_ordenadas[0]
        fecha_ultimo = obtener_fecha_postventa(ultimo)
        dias_desde = (hoy - fecha_ultimo).days if fecha_ultimo else None

        km_ultimo = extraer_numero_entero(ultimo.ore_kilometraje)
        km_recorridos = None
        if (
            kilometraje_actual_num is not None
            and km_ultimo is not None
            and kilometraje_actual_num >= km_ultimo
        ):
            km_recorridos = kilometraje_actual_num - km_ultimo

        resumen.append(
            {
                "clave": servicio["clave"],
                "nombre": servicio["nombre"],
                "ultima_fecha": fecha_ultimo,
                "dias_desde": dias_desde,
                "ultimo_kilometraje": ultimo.ore_kilometraje,
                "kilometros_recorridos_desde_ultimo": km_recorridos,
                "ultima_orden": ultimo.ore_idorden,
                "asesor": ultimo.asesor,
                "tecnico": ultimo.tecnico,
                "descripcion": obtener_descripcion_postventa(ultimo),
                "estatus_revision": calcular_estatus_revision(
                    dias_desde=dias_desde,
                    intervalo_dias=servicio["intervalo_dias"],
                ),
                "intervalo_dias_referencial": servicio["intervalo_dias"],
            }
        )

    return sorted(
        resumen,
        key=lambda item: (
            item["dias_desde"] is None,
            -(item["dias_desde"] or 0),
        ),
    )


def construir_trabajos_recientes(historial, limite=8):
    trabajos = []
    vistos = set()

    historial_ordenado = sorted(
        historial,
        key=lambda item: (
            obtener_fecha_postventa(item) or date.min,
            str(item.ore_idorden or ""),
        ),
        reverse=True,
    )

    for item in historial_ordenado:
        descripcion = obtener_descripcion_postventa(item)
        descripcion_normalizada = normalizar_texto(descripcion)

        if not descripcion_normalizada or descripcion_normalizada in vistos:
            continue

        vistos.add(descripcion_normalizada)
        trabajos.append(
            {
                "descripcion": descripcion,
                "fecha": obtener_fecha_postventa(item),
                "orden": item.ore_idorden,
                "kilometraje": item.ore_kilometraje,
            }
        )

        if len(trabajos) >= limite:
            break

    return trabajos


def obtener_query_param(query_params, *nombres):
    for nombre in nombres:
        valor = query_params.get(nombre)
        if valor not in (None, ""):
            return valor
    return None


def aplicar_filtro_numerico(queryset, campo, operador, valor):
    if operador in (None, "") or valor in (None, ""):
        return queryset

    numero = extraer_numero_entero(valor)
    if numero is None:
        return queryset

    operador_normalizado = str(operador).strip().lower()
    mapa_operadores = {
        "mayor": "gt",
        "menor": "lt",
        "igual": "exact",
    }
    lookup = mapa_operadores.get(operador_normalizado)

    if not lookup:
        return queryset

    return queryset.filter(**{f"{campo}__{lookup}": numero})


class OrdenServicioVentaDiautosViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrdenServicioVentaDiautosSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    http_method_names = ["get", "head", "options"]
    pagination_class = RetencionPagination

    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        "id",
        "fecha_venta",
        "fecha_os",
        "ano_modelo",
        "importe_factura",
        "costo_os",
        "dias_os_a_actual",
        "meses_actual_a_venta",
        "prioridad_prospeccion",
    ]
    ordering = ["-dias_os_a_actual", "-id"]

    def get_queryset(self):
        queryset = OrdenServicioVentaDiautos.objects.all()
        query_params = self.request.query_params

        q = query_params.get("q")
        vendedor = query_params.get("vendedor")
        asesor = query_params.get("asesor")
        estado_os = query_params.get("estado_os")
        clasificacion = query_params.get("clasificacion")
        marca_vehiculo = query_params.get("marca_vehiculo")
        fecha_venta_desde = query_params.get("fecha_venta_desde")
        fecha_venta_hasta = query_params.get("fecha_venta_hasta")
        fecha_os_desde = query_params.get("fecha_os_desde")
        fecha_os_hasta = query_params.get("fecha_os_hasta")

        nombre_cte = obtener_query_param(
            query_params,
            "nombre_cte",
            "nombre",
            "nombre_cte__icontains",
            "nombre__icontains",
        )
        numero_serie = obtener_query_param(
            query_params,
            "numero_serie",
            "vin",
            "numero_serie__icontains",
            "vin__icontains",
        )
        celular = obtener_query_param(
            query_params,
            "celular",
            "celular__icontains",
        )
        email = obtener_query_param(
            query_params,
            "email",
            "email__icontains",
        )
        meses_desde = obtener_query_param(query_params, "meses_desde", "mesesDesde")
        meses_hasta = obtener_query_param(query_params, "meses_hasta", "mesesHasta")
        franja_retencion = query_params.get("franja_retencion")
        estado_cliente = query_params.get("estado_cliente")
        prioridad_prospeccion = obtener_query_param(
            query_params,
            "prioridad_prospeccion",
            "prioridadProspeccion",
            "prioridad_prospeccion__iexact",
        )

        dias_operador = obtener_query_param(
            query_params,
            "dias_operador",
            "operadorDiasIngreso",
        )
        dias_valor = obtener_query_param(
            query_params,
            "dias_valor",
            "valorDiasIngreso",
        )
        meses_venta_operador = obtener_query_param(
            query_params,
            "meses_venta_operador",
            "operadorMesesVenta",
        )
        meses_venta_valor = obtener_query_param(
            query_params,
            "meses_venta_valor",
            "valorMesesVenta",
        )

        dias_gt = query_params.get("dias_os_a_actual__gt")
        dias_lt = query_params.get("dias_os_a_actual__lt")
        dias_exact = query_params.get("dias_os_a_actual__exact")

        meses_gt = query_params.get("meses_actual_a_venta__gt")
        meses_lt = query_params.get("meses_actual_a_venta__lt")
        meses_exact = query_params.get("meses_actual_a_venta__exact")

        if q:
            queryset = queryset.filter(
                Q(nombre_cte__icontains=q)
                | Q(telefono__icontains=q)
                | Q(celular__icontains=q)
                | Q(email__icontains=q)
                | Q(marca_vehiculo__icontains=q)
                | Q(version__icontains=q)
                | Q(numero_serie__icontains=q)
                | Q(vendedor__icontains=q)
                | Q(asesor__icontains=q)
                | Q(folio_factura__icontains=q)
                | Q(id_os__icontains=q)
                | Q(tipo_orden_servicio__icontains=q)
                | Q(estado_os__icontains=q)
                | Q(clasificacion__icontains=q)
                | Q(franja_retencion__icontains=q)
                | Q(prioridad_prospeccion__icontains=q)
            )

        if vendedor:
            queryset = queryset.filter(vendedor__icontains=vendedor)

        if asesor:
            queryset = queryset.filter(asesor__icontains=asesor)

        if estado_os:
            queryset = queryset.filter(estado_os__iexact=estado_os)

        if clasificacion:
            queryset = queryset.filter(clasificacion__iexact=clasificacion)

        if marca_vehiculo:
            queryset = queryset.filter(marca_vehiculo__icontains=marca_vehiculo)

        if fecha_venta_desde:
            queryset = queryset.filter(fecha_venta__gte=fecha_venta_desde)

        if fecha_venta_hasta:
            queryset = queryset.filter(fecha_venta__lte=fecha_venta_hasta)

        if fecha_os_desde:
            queryset = queryset.filter(fecha_os__gte=fecha_os_desde)

        if fecha_os_hasta:
            queryset = queryset.filter(fecha_os__lte=fecha_os_hasta)

        if nombre_cte:
            queryset = queryset.filter(nombre_cte__icontains=nombre_cte)

        if numero_serie:
            queryset = queryset.filter(numero_serie__icontains=numero_serie)

        if celular:
            queryset = queryset.filter(celular__icontains=celular)

        if email:
            queryset = queryset.filter(email__icontains=email)

        if meses_desde not in (None, ""):
            queryset = queryset.filter(meses_actual_a_venta__gte=meses_desde)

        if meses_hasta not in (None, ""):
            queryset = queryset.filter(meses_actual_a_venta__lte=meses_hasta)

        if franja_retencion:
            queryset = queryset.filter(franja_retencion__iexact=franja_retencion)

        if estado_cliente:
            queryset = queryset.filter(estado_cliente__iexact=estado_cliente)

        if prioridad_prospeccion:
            queryset = queryset.filter(
                prioridad_prospeccion__iexact=prioridad_prospeccion
            )

        if dias_gt not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "dias_os_a_actual",
                "mayor",
                dias_gt,
            )
        elif dias_lt not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "dias_os_a_actual",
                "menor",
                dias_lt,
            )
        elif dias_exact not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "dias_os_a_actual",
                "igual",
                dias_exact,
            )
        else:
            queryset = aplicar_filtro_numerico(
                queryset,
                "dias_os_a_actual",
                dias_operador,
                dias_valor,
            )

        if meses_gt not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "meses_actual_a_venta",
                "mayor",
                meses_gt,
            )
        elif meses_lt not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "meses_actual_a_venta",
                "menor",
                meses_lt,
            )
        elif meses_exact not in (None, ""):
            queryset = aplicar_filtro_numerico(
                queryset,
                "meses_actual_a_venta",
                "igual",
                meses_exact,
            )
        else:
            queryset = aplicar_filtro_numerico(
                queryset,
                "meses_actual_a_venta",
                meses_venta_operador,
                meses_venta_valor,
            )

        return queryset

    @action(
        detail=False,
        methods=["get"],
        url_path="estadisticas",
        permission_classes=[permissions.AllowAny],
        authentication_classes=[],
    )
    def estadisticas(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.count()
        activos = queryset.filter(estado_cliente__iexact="ACTIVO").count()
        inactivos = queryset.filter(estado_cliente__iexact="INACTIVO").count()

        porcentaje_retorno = round((activos / total) * 100, 2) if total else 0

        acumulado_modelos = defaultdict(
            lambda: {"nombre": "", "activo": 0, "inactivo": 0}
        )

        for version, estado in queryset.values_list("version", "estado_cliente"):
            modelo = obtener_modelo_desde_version(version)
            acumulado_modelos[modelo]["nombre"] = modelo

            if str(estado or "").upper() == "ACTIVO":
                acumulado_modelos[modelo]["activo"] += 1
            else:
                acumulado_modelos[modelo]["inactivo"] += 1

        modelos = sorted(
            acumulado_modelos.values(),
            key=lambda item: (item["activo"] + item["inactivo"]),
            reverse=True,
        )[:10]

        return Response(
            {
                "porcentaje_retorno": porcentaje_retorno,
                "vines_segmento": total,
                "vines_activos": activos,
                "vines_inactivos": inactivos,
                "modelos": modelos,
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="detalle-comercial",
        permission_classes=[permissions.AllowAny],
        authentication_classes=[],
    )
    def detalle_comercial(self, request, pk=None):
        registro = self.get_object()
        vin = str(registro.numero_serie or "").strip()

        historial_qs = DetalleVentasPostVentaLimpia.objects.none()
        if vin:
            historial_qs = DetalleVentasPostVentaLimpia.objects.filter(
                ore_numserie__iexact=vin
            ).order_by("-ore_fechaord", "-ore_fechacie", "-vte_fechdocto", "-ore_idorden")

        historial = list(historial_qs[:250])

        historial_ordenado = sorted(
            historial,
            key=lambda item: (
                obtener_fecha_postventa(item) or date.min,
                str(item.ore_idorden or ""),
            ),
            reverse=True,
        )

        ultimo_registro = historial_ordenado[0] if historial_ordenado else None
        fecha_ultimo_historial = (
            obtener_fecha_postventa(ultimo_registro) if ultimo_registro else None
        )

        dias_desde_ultimo_historial = None
        if fecha_ultimo_historial:
            dias_desde_ultimo_historial = (date.today() - fecha_ultimo_historial).days

        return Response(
            {
                "registro": OrdenServicioVentaDiautosSerializer(registro).data,
                "resumen": {
                    "vin": vin,
                    "total_ordenes_historial": len(historial_ordenado),
                    "ultima_fecha_historial": fecha_ultimo_historial,
                    "dias_desde_ultimo_historial": dias_desde_ultimo_historial,
                    "dias_os_a_actual": registro.dias_os_a_actual,
                    "ultimo_kilometraje_historial": (
                        ultimo_registro.ore_kilometraje if ultimo_registro else None
                    ),
                    "ultimo_asesor": ultimo_registro.asesor if ultimo_registro else None,
                    "ultimo_tecnico": ultimo_registro.tecnico if ultimo_registro else None,
                    "ultima_orden": ultimo_registro.ore_idorden if ultimo_registro else None,
                },
                "servicios_relevantes": construir_resumen_servicios(
                    historial=historial_ordenado,
                    kilometraje_actual=registro.kilometraje,
                ),
                "trabajos_recientes": construir_trabajos_recientes(historial_ordenado),
                "historial": DetalleVentasPostVentaLimpiaSerializer(
                    historial_ordenado,
                    many=True,
                ).data,
            }
        )