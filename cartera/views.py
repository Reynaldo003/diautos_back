# cartera/views.py
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from retencion.models import OrdenServicioVentaDiautos
from usuarios.auth import obtener_usuario_desde_request
from usuarios.models import Usuario

from .models import CarteraCliente, obtener_modelo_desde_version
from .serializers import (
    CarteraAsignacionAutomaticaSerializer,
    CarteraClienteManualSerializer,
    CarteraClienteSerializer,
    UsuarioBDCSerializer,
)


class CarteraPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


def obtener_rango_mes_anterior():
    hoy = timezone.localdate()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    return primer_dia_mes_anterior, ultimo_dia_mes_anterior


def limpiar_texto(valor):
    return str(valor or "").strip()


def normalizar_vin(valor):
    return limpiar_texto(valor).upper()


def obtener_usuario_actual(request):
    try:
        return obtener_usuario_desde_request(request)
    except Exception:
        return None


def construir_payload_desde_venta(venta, asesor, creado_por=None, origen="AUTOMATICO"):
    return {
        "venta": venta,
        "vin": normalizar_vin(venta.numero_serie),
        "vin_normalizado": normalizar_vin(venta.numero_serie),
        "nombre_cliente": venta.nombre_cte,
        "telefono": venta.telefono,
        "celular": venta.celular,
        "email": venta.email,
        "marca_vehiculo": venta.marca_vehiculo,
        "modelo": obtener_modelo_desde_version(venta.version),
        "version": venta.version,
        "ano_modelo": venta.ano_modelo,
        "fecha_venta": venta.fecha_venta,
        "folio_factura": venta.folio_factura,
        "vendedor": venta.vendedor,
        "fecha_os": venta.fecha_os,
        "id_os": venta.id_os,
        "asesor_servicio": venta.asesor,
        "estado_cliente": venta.estado_cliente,
        "dias_os_a_actual": venta.dias_os_a_actual,
        "meses_actual_a_venta": venta.meses_actual_a_venta,
        "franja_retencion": venta.franja_retencion,
        "prioridad_prospeccion": venta.prioridad_prospeccion,
        "kilometraje": venta.kilometraje,
        "asesor_asignado": asesor,
        "creado_por": creado_por,
        "origen": origen,
    }


def obtener_ventas_base(fecha_venta_desde=None, fecha_venta_hasta=None):
    if not fecha_venta_desde or not fecha_venta_hasta:
        fecha_venta_desde, fecha_venta_hasta = obtener_rango_mes_anterior()

    queryset = (
        OrdenServicioVentaDiautos.objects.filter(
            fecha_venta__gte=fecha_venta_desde,
            fecha_venta__lte=fecha_venta_hasta,
        )
        .exclude(numero_serie__isnull=True)
        .exclude(numero_serie="")
        .order_by("fecha_venta", "ano_modelo", "version", "numero_serie", "id")
    )

    vines_ya_asignados = set(
        CarteraCliente.objects.filter(activo=True)
        .values_list("vin_normalizado", flat=True)
    )

    ventas_unicas_por_vin = {}

    for venta in queryset:
        vin = normalizar_vin(venta.numero_serie)

        if not vin or vin in vines_ya_asignados:
            continue

        venta_actual = ventas_unicas_por_vin.get(vin)

        if venta_actual is None:
            ventas_unicas_por_vin[vin] = venta
            continue

        fecha_actual = venta_actual.fecha_venta or date.min
        fecha_nueva = venta.fecha_venta or date.min

        if (fecha_nueva, venta.id) > (fecha_actual, venta_actual.id):
            ventas_unicas_por_vin[vin] = venta

    return list(ventas_unicas_por_vin.values())


def construir_llave_segmento(venta):
    modelo = obtener_modelo_desde_version(venta.version)

    return (
        venta.meses_actual_a_venta if venta.meses_actual_a_venta is not None else -1,
        venta.ano_modelo if venta.ano_modelo is not None else -1,
        modelo,
    )


def distribuir_ventas_equilibradas(ventas, asesores):
    """
    Distribuye intentando mantener balance global y balance por segmento:
    meses desde venta + año modelo + modelo.
    """
    asesores = list(asesores)
    if not asesores:
        return []

    ventas_por_segmento = defaultdict(list)

    for venta in ventas:
        ventas_por_segmento[construir_llave_segmento(venta)].append(venta)

    for segmento in ventas_por_segmento:
        ventas_por_segmento[segmento].sort(
            key=lambda item: (
                item.fecha_venta or date.min,
                item.ano_modelo or 0,
                obtener_modelo_desde_version(item.version),
                item.id,
            )
        )

    total_por_asesor = Counter()
    total_segmento_por_asesor = defaultdict(Counter)

    asignaciones = []

    for segmento in sorted(ventas_por_segmento.keys()):
        for venta in ventas_por_segmento[segmento]:
            asesor = min(
                asesores,
                key=lambda item: (
                    total_por_asesor[item.id_usuario],
                    total_segmento_por_asesor[segmento][item.id_usuario],
                    item.id_usuario,
                ),
            )

            total_por_asesor[asesor.id_usuario] += 1
            total_segmento_por_asesor[segmento][asesor.id_usuario] += 1

            asignaciones.append({
                "venta": venta,
                "asesor": asesor,
                "segmento": {
                    "meses_actual_a_venta": venta.meses_actual_a_venta,
                    "ano_modelo": venta.ano_modelo,
                    "modelo": obtener_modelo_desde_version(venta.version),
                },
            })

    return asignaciones


def construir_resumen_preview(asignaciones):
    resumen_asesores = defaultdict(lambda: {
        "asesor_id": None,
        "asesor_nombre": "",
        "total": 0,
        "por_modelo": defaultdict(int),
        "por_ano_modelo": defaultdict(int),
        "por_meses_venta": defaultdict(int),
    })

    for item in asignaciones:
        asesor = item["asesor"]
        venta = item["venta"]
        asesor_id = asesor.id_usuario
        modelo = obtener_modelo_desde_version(venta.version)
        ano = str(venta.ano_modelo or "SIN AÑO")
        meses = str(
            venta.meses_actual_a_venta
            if venta.meses_actual_a_venta is not None
            else "SIN MESES"
        )

        resumen = resumen_asesores[asesor_id]
        resumen["asesor_id"] = asesor_id
        resumen["asesor_nombre"] = f"{asesor.nombre} {asesor.apellidos or ''}".strip()
        resumen["total"] += 1
        resumen["por_modelo"][modelo] += 1
        resumen["por_ano_modelo"][ano] += 1
        resumen["por_meses_venta"][meses] += 1

    respuesta = []

    for resumen in resumen_asesores.values():
        respuesta.append({
            "asesor_id": resumen["asesor_id"],
            "asesor_nombre": resumen["asesor_nombre"],
            "total": resumen["total"],
            "por_modelo": dict(resumen["por_modelo"]),
            "por_ano_modelo": dict(resumen["por_ano_modelo"]),
            "por_meses_venta": dict(resumen["por_meses_venta"]),
        })

    return sorted(respuesta, key=lambda item: item["asesor_nombre"])


class CarteraClienteViewSet(viewsets.ModelViewSet):
    serializer_class = CarteraClienteSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = CarteraPagination
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = (
            CarteraCliente.objects.filter(activo=True)
            .select_related("asesor_asignado", "creado_por", "venta")
            .order_by("-asignado_en", "-id")
        )

        params = self.request.query_params

        q = limpiar_texto(params.get("q"))
        asesor_id = limpiar_texto(params.get("asesor_id"))
        estado_gestion = limpiar_texto(params.get("estado_gestion"))
        fecha_venta_desde = limpiar_texto(params.get("fecha_venta_desde"))
        fecha_venta_hasta = limpiar_texto(params.get("fecha_venta_hasta"))
        fecha_asignacion_desde = limpiar_texto(params.get("fecha_asignacion_desde"))
        fecha_asignacion_hasta = limpiar_texto(params.get("fecha_asignacion_hasta"))
        mi_cartera = limpiar_texto(params.get("mi_cartera")).lower()

        if q:
            queryset = queryset.filter(
                Q(nombre_cliente__icontains=q)
                | Q(vin__icontains=q)
                | Q(celular__icontains=q)
                | Q(telefono__icontains=q)
                | Q(email__icontains=q)
                | Q(version__icontains=q)
                | Q(modelo__icontains=q)
                | Q(folio_factura__icontains=q)
            )

        if asesor_id:
            queryset = queryset.filter(asesor_asignado_id=asesor_id)

        if estado_gestion:
            queryset = queryset.filter(estado_gestion=estado_gestion)

        if fecha_venta_desde:
            queryset = queryset.filter(fecha_venta__gte=fecha_venta_desde)

        if fecha_venta_hasta:
            queryset = queryset.filter(fecha_venta__lte=fecha_venta_hasta)

        if fecha_asignacion_desde:
            queryset = queryset.filter(asignado_en__date__gte=fecha_asignacion_desde)

        if fecha_asignacion_hasta:
            queryset = queryset.filter(asignado_en__date__lte=fecha_asignacion_hasta)

        if mi_cartera in ("1", "true", "si", "sí"):
            usuario = obtener_usuario_actual(self.request)

            if usuario:
                queryset = queryset.filter(asesor_asignado=usuario)
            else:
                queryset = queryset.none()

        return queryset

    def partial_update(self, request, *args, **kwargs):
        """
        Permitimos actualizar solo el estado de gestión.
        No permitimos cambiar el asesor porque la asignación debe ser permanente.
        """
        instancia = self.get_object()
        estado_gestion = request.data.get("estado_gestion")

        if not estado_gestion:
            return Response(
                {"detail": "El campo estado_gestion es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estados_validos = [
            opcion[0] for opcion in CarteraCliente.EstadoGestion.choices
        ]

        if estado_gestion not in estados_validos:
            return Response(
                {"detail": "Estado de gestión inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instancia.estado_gestion = estado_gestion
        instancia.save(update_fields=["estado_gestion", "actualizado_en"])

        return Response(CarteraClienteSerializer(instancia).data)

    @action(detail=False, methods=["get"], url_path="asesores-bdc")
    def asesores_bdc(self, request):
        agencia = limpiar_texto(request.query_params.get("agencia"))

        queryset = Usuario.objects.select_related("rol").filter(
            Q(rol__nombre__icontains="BDC")
            | Q(rol__nombre__icontains="Digital")
            | Q(rol__nombre__icontains="Posventa")
            | Q(rol__nombre__icontains="Servicio")
        ).order_by("nombre", "apellidos")

        if agencia:
            queryset = queryset.filter(agencia__iexact=agencia)

        return Response(UsuarioBDCSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.count()
        pendientes = queryset.filter(
            estado_gestion=CarteraCliente.EstadoGestion.PENDIENTE
        ).count()
        contactados = queryset.filter(
            estado_gestion=CarteraCliente.EstadoGestion.CONTACTADO
        ).count()
        citas = queryset.filter(
            estado_gestion=CarteraCliente.EstadoGestion.CITA_AGENDADA
        ).count()

        por_asesor = (
            queryset.values(
                "asesor_asignado_id",
                "asesor_asignado__nombre",
                "asesor_asignado__apellidos",
            )
            .annotate(total=Count("id"))
            .order_by("asesor_asignado__nombre")
        )

        por_modelo = (
            queryset.values("modelo")
            .annotate(total=Count("id"))
            .order_by("-total")[:15]
        )

        por_ano_modelo = (
            queryset.values("ano_modelo")
            .annotate(total=Count("id"))
            .order_by("-ano_modelo")
        )

        return Response({
            "total": total,
            "pendientes": pendientes,
            "contactados": contactados,
            "citas": citas,
            "por_asesor": [
                {
                    "asesor_id": item["asesor_asignado_id"],
                    "asesor_nombre": (
                        f"{item['asesor_asignado__nombre']} "
                        f"{item['asesor_asignado__apellidos'] or ''}"
                    ).strip(),
                    "total": item["total"],
                }
                for item in por_asesor
            ],
            "por_modelo": list(por_modelo),
            "por_ano_modelo": list(por_ano_modelo),
        })

    @action(detail=False, methods=["get"], url_path="ventas-disponibles")
    def ventas_disponibles(self, request):
        fecha_venta_desde = request.query_params.get("fecha_venta_desde")
        fecha_venta_hasta = request.query_params.get("fecha_venta_hasta")

        ventas = obtener_ventas_base(
            fecha_venta_desde=fecha_venta_desde,
            fecha_venta_hasta=fecha_venta_hasta,
        )

        data = []

        for venta in ventas[:500]:
            data.append({
                "venta_id": venta.id,
                "vin": venta.numero_serie,
                "nombre_cliente": venta.nombre_cte,
                "fecha_venta": venta.fecha_venta,
                "ano_modelo": venta.ano_modelo,
                "modelo": obtener_modelo_desde_version(venta.version),
                "version": venta.version,
                "meses_actual_a_venta": venta.meses_actual_a_venta,
                "celular": venta.celular,
                "telefono": venta.telefono,
                "email": venta.email,
            })

        return Response({
            "total": len(ventas),
            "results": data,
        })

    @action(detail=False, methods=["post"], url_path="asignar-automatico")
    def asignar_automatico(self, request):
        serializer = CarteraAsignacionAutomaticaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asesores_ids = serializer.validated_data["asesores_ids"]
        fecha_venta_desde = serializer.validated_data.get("fecha_venta_desde")
        fecha_venta_hasta = serializer.validated_data.get("fecha_venta_hasta")
        simular = serializer.validated_data.get("simular", False)

        asesores = list(
            Usuario.objects.filter(id_usuario__in=asesores_ids)
            .select_related("rol")
            .order_by("id_usuario")
        )

        ventas = obtener_ventas_base(
            fecha_venta_desde=fecha_venta_desde,
            fecha_venta_hasta=fecha_venta_hasta,
        )

        asignaciones = distribuir_ventas_equilibradas(ventas, asesores)
        resumen = construir_resumen_preview(asignaciones)

        if simular:
            return Response({
                "simulacion": True,
                "total_disponibles": len(ventas),
                "total_asignables": len(asignaciones),
                "resumen": resumen,
            })

        usuario_actual = obtener_usuario_actual(request)
        creados = []
        omitidos = []

        with transaction.atomic():
            for item in asignaciones:
                venta = item["venta"]
                asesor = item["asesor"]
                vin = normalizar_vin(venta.numero_serie)

                try:
                    cartera = CarteraCliente.objects.create(
                        **construir_payload_desde_venta(
                            venta=venta,
                            asesor=asesor,
                            creado_por=usuario_actual,
                            origen="AUTOMATICO",
                        )
                    )
                    creados.append(cartera)
                except IntegrityError:
                    omitidos.append({
                        "vin": vin,
                        "motivo": "El VIN ya tenía una asignación previa.",
                    })

        return Response(
            {
                "simulacion": False,
                "total_disponibles": len(ventas),
                "total_creados": len(creados),
                "total_omitidos": len(omitidos),
                "omitidos": omitidos,
                "resumen": resumen,
                "results": CarteraClienteSerializer(creados, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="crear-cliente-manual")
    def crear_cliente_manual(self, request):
        usuario_actual = obtener_usuario_actual(request)

        if not usuario_actual:
            return Response(
                {"detail": "No se pudo identificar al usuario actual."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = CarteraClienteManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        cartera = CarteraCliente.objects.create(
            vin=data["vin"],
            vin_normalizado=data["vin"],
            nombre_cliente=data["nombre_cliente"],
            telefono=data.get("telefono", ""),
            celular=data.get("celular", ""),
            email=data.get("email", ""),
            marca_vehiculo=data.get("marca_vehiculo", ""),
            version=data.get("version", ""),
            modelo=obtener_modelo_desde_version(data.get("version", "")),
            ano_modelo=data.get("ano_modelo"),
            asesor_asignado=usuario_actual,
            creado_por=usuario_actual,
            origen="MANUAL",
        )

        return Response(
            CarteraClienteSerializer(cartera).data,
            status=status.HTTP_201_CREATED,
        )