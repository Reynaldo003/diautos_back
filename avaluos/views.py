from io import BytesIO
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from usuarios.authentication import SignedUserAuthentication
from .models import AvaluoUsado
from .serializers import AvaluoUsadoSerializer


CHECKLIST_100 = [
    "Vehículo ha sufrido modificaciones",
    "Costado derecho y alineación de puertas",
    "Costado izquierdo y alineación de puertas",
    "Defensa delantera",
    "Cofre",
    "Todos cristales",
    "Defensa trasera",
    "Tapa de gasolina",
    "Tapa cajuela / cajuela / bedliner",
    "Cajuela",
    "Rines y ruedas / cubierta de neumáticos / biseles / tapones",
    "Cristal",
    "Estribos",
    "Retrovisores",
    "Antena",
    "Sellos, gomas, empaques de puertas",
    "Puertas / cerraduras",
    "Luces exteriores",
    "Alarma",
    "Encendido remoto",
    "Freno de estacionamiento",
    "Asientos / anclaje de seguridad para niños",
    "Cinturones",
    "Cristales",
    "Quemacocos",
    "Sistema de navegación",
    "Sistema de audio y DVD",
    "Conectividad USB / AUX / Bluetooth",
    "Reloj / termómetro",
    "Computadora de viaje",
    "Toma corriente",
    "Luces de interior",
    "Desempañador trasero",
    "Panel de instrumentos",
    "Asientos traseros / reposacabezas",
    "Consola / compartimiento delantero trasero",
    "Presionar botón",
    "Verificar conectividad de módulo",
    "Escaneo de vehículo",
    "Detectar códigos motor",
    "Sensores",
    "Medidores / tonos de aviso",
    "Encendido y estabilidad motor",
    "Funcionamiento motor / desempeño / aceleración",
    "Transmisión automático / manual",
    "Control de tracción",
    "Frenos / ABS",
    "Dirección / alineación y balanceo",
    "Chasis / alineación",
    "Caja de transferencia",
    "Control de crucero",
    "Velocímetro / tacómetro / odómetro",
    "Calentador / aire acondicionado",
    "Volante telescópico y altura",
    "Claxon",
    "Limpiaparabrisas / chisgueteros / plumas",
    "Ajustes de pedales / volante",
    "Inspección visual bajo cofre",
    "Calcomanías de marca debajo del cofre",
    "Sistema de enfriamiento motor / radiador / mangueras",
    "Sistema de dirección",
    "Sistema eléctrico",
    "Sistema de frenos",
    "Sistema de encendido",
    "Sistema de combustible",
    "Compresor A/C",
    "Inspección de filtros",
    "Inspección de mangueras",
    "Inspección bandas",
    "Prueba de batería",
    "Prueba de compresión / fugas / degradación de aceite motor",
    "Catalizador / sensores de oxígeno / emisiones",
    "Prueba de eficiencia de A/C",
    "Visual bajo vehículo",
    "Marcas de reparación / daños",
    "Pastillas de freno / balatas",
    "Discos / pinzas / calipers / tambores",
    "Freno hidráulico",
    "Neumáticos",
    "Rueda de acero / aleación originales",
    "Amortiguadores",
    "Soportes motor / caja / escape",
    "Dirección / enlace",
    "Compartimiento del motor",
    "Motor",
    "Transmisión",
    "Caja de transferencia",
    "Montaje / ejes",
    "Diferencial",
    "Manual de propietario",
    "Campañas abiertas",
    "Vehículo es certificable",
    "Fecha de último mantenimiento",
    "Detallado exterior e interior",
    "Pre-activación completada",
    "Prueba de estado de salud de batería",
    "Realizar campañas abiertas",
    "Cambio de aceite de motor y filtro",
    "Inspeccionar / cambiar filtros",
    "Inspeccionar y poner a nivel todos los fluidos",
]


def normalizar_rol(request):
    rol = getattr(request.user, "rol", "") or ""
    return str(rol).strip().lower()


def es_admin_o_valuador(request):
    rol = normalizar_rol(request)
    permisos = getattr(request.user, "permisos", []) or []

    return (
        "administrador" in rol
        or "valuador" in rol
        or "all" in [str(p).lower() for p in permisos]
        or "usuarios_admin" in [str(p).lower() for p in permisos]
    )


def es_tecnico(request):
    rol = normalizar_rol(request)
    return "tecnico" in rol or "técnico" in rol


def fmt_fecha(valor):
    if not valor:
        return "—"

    try:
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def texto(valor, default="—"):
    valor = "" if valor is None else str(valor).strip()
    return valor or default


def moneda(valor):
    try:
        numero = Decimal(str(valor or "0"))
    except Exception:
        numero = Decimal("0")

    return f"${numero:,.2f}"


def estado_checklist(valor):
    mapa = {
        "inspeccion_realizada": "Inspección realizada",
        "requiere_servicio": "Requiere servicio",
        "servicio_realizado": "Servicio realizado",
        "na": "N/A",
        "si": "Sí",
        "no": "No",
    }

    return mapa.get(str(valor or "").strip().lower(), "")


def pdf_response(story, filename):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )

    doc.build(story)

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def tabla(data, col_widths=None):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def generar_ticket_pdf(avaluo):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Solicitud de Servicio y Refacciones - Cargo Interno", styles["Title"]))
    story.append(Paragraph("Seminuevos Certificados Chevrolet", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(tabla([
        ["Dato", "Valor", "Dato", "Valor"],
        ["Asesor", texto(avaluo.asesor_ventas), "Generado", timezone.localtime().strftime("%d/%m/%Y %H:%M")],
        ["Responsable solicitud", "", "Responsable autorización", ""],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos del vehículo", styles["Heading2"]))
    story.append(tabla([
        ["Campo", "Valor", "Campo", "Valor"],
        ["Marca", texto(avaluo.marca_auto), "Color", texto(avaluo.color)],
        ["Modelo", texto(avaluo.modelo), "Año", texto(avaluo.anio_modelo)],
        ["No. Serie", texto(avaluo.serie), "Versión", texto(avaluo.version)],
        ["Vendedor", texto(avaluo.vendedor or avaluo.asesor_ventas), "Placas", texto(avaluo.placas)],
        ["KM", texto(avaluo.kilometraje), "Fecha avalúo", fmt_fecha(avaluo.fecha_avaluo)],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Comentarios", styles["Heading2"]))
    story.append(Paragraph(texto(avaluo.comentarios, "Valuación"), styles["Normal"]))

    story.append(Spacer(1, 35))

    story.append(tabla([
        ["Responsable de solicitud", "Responsable de autorización"],
        ["\n\nNombre y firma", "\n\nNombre y firma"],
    ], [9 * cm, 9 * cm]))

    return pdf_response(story, f"ticket_avaluo_{avaluo.id}.pdf")


def generar_checklist_pdf(avaluo):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("100 Puntos Checklist", styles["Title"]))
    story.append(Paragraph("Valuación y Certificación de Unidad", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos generales", styles["Heading2"]))

    cliente = avaluo.cliente

    story.append(tabla([
        ["Campo", "Valor", "Campo", "Valor"],
        ["Cliente", texto(cliente.nombre), "Teléfono", texto(cliente.telefono)],
        ["Correo", texto(cliente.correo), "Agencia", texto(avaluo.agencia)],
        ["Asesor", texto(avaluo.asesor_ventas), "Fecha avalúo", fmt_fecha(avaluo.fecha_avaluo)],
        ["Tipo valuación", texto(avaluo.get_tipo_valuacion_display()), "Tipo toma", texto(avaluo.get_tipo_toma_display())],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos del coche", styles["Heading2"]))
    story.append(tabla([
        ["Campo", "Valor", "Campo", "Valor"],
        ["Marca", texto(avaluo.marca_auto), "Modelo", texto(avaluo.modelo)],
        ["Año", texto(avaluo.anio_modelo), "Versión", texto(avaluo.version)],
        ["No. Serie", texto(avaluo.serie), "Placas", texto(avaluo.placas)],
        ["Color", texto(avaluo.color), "KM", texto(avaluo.kilometraje)],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Checklist 100 puntos", styles["Heading2"]))

    checklist = avaluo.checklist_100 or {}

    data = [["#", "Punto", "Estado"]]

    for index, descripcion in enumerate(CHECKLIST_100, start=1):
        data.append([
            str(index),
            descripcion,
            estado_checklist(checklist.get(str(index))),
        ])

    story.append(tabla(data, [1.1 * cm, 12.5 * cm, 4.5 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Costos", styles["Heading2"]))
    story.append(tabla([
        ["Concepto", "Total"],
        ["Mecánica", moneda(avaluo.costo_mecanica_total)],
        ["Total reparación", moneda(avaluo.costo_reparacion)],
        ["Oferta inicial", texto(avaluo.oferta_inicial)],
        ["Oferta final", texto(avaluo.oferta_final)],
    ], [8 * cm, 8 * cm]))

    story.append(Spacer(1, 25))

    story.append(tabla([
        ["Responsable de solicitud", "Responsable de autorización", "Valuador - Comprador"],
        ["\n\nNombre y firma", "\n\nNombre y firma", "\n\nNombre y firma"],
    ], [6 * cm, 6 * cm, 6 * cm]))

    return pdf_response(story, f"checklist_100_avaluo_{avaluo.id}.pdf")


class AvaluoUsadoViewSet(viewsets.ModelViewSet):
    authentication_classes = [SignedUserAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    queryset = (
        AvaluoUsado.objects
        .select_related("cliente")
        .prefetch_related("evidencias", "conceptos")
        .all()
        .order_by("-creado")
    )
    serializer_class = AvaluoUsadoSerializer
    filter_backends = [OrderingFilter, SearchFilter]

    ordering_fields = [
        "creado",
        "actualizado",
        "fecha_avaluo",
        "fecha_finalizacion",
        "fecha_toma_cuenta",
        "agenda_valuacion",
        "agencia",
        "asesor_ventas",
        "marca_auto",
        "modelo",
        "anio_modelo",
        "serie",
        "placas",
        "kilometraje",
        "precio_guia",
        "costo_reparacion",
        "costo_estimado",
        "oferta_inicial",
        "oferta_final",
        "color",
        "ganador_subasta",
        "etapa_proceso",
        "tipo_toma",
        "tipo_valuacion",
    ]

    search_fields = [
        "agencia",
        "asesor_ventas",
        "vendedor",
        "marca_auto",
        "modelo",
        "anio_modelo",
        "version",
        "serie",
        "placas",
        "kilometraje",
        "precio_guia",
        "precio_compra_libro_azul",
        "precio_venta_libro_azul",
        "costo_reparacion",
        "costo_estimado",
        "oferta_inicial",
        "oferta_final",
        "color",
        "descripcion",
        "observaciones",
        "comentarios",
        "origen_valuacion",
        "ganador_subasta",
        "etapa_proceso",
        "tipo_toma",
        "tipo_valuacion",
        "conceptos__descripcion",
        "evidencias__descripcion",
        "cliente__nombre",
        "cliente__telefono",
        "cliente__correo",
    ]

    def get_queryset(self):
        qs = super().get_queryset()

        if es_admin_o_valuador(self.request):
            return qs

        agencia = str(getattr(self.request.user, "agencia", "") or "").strip()

        if agencia:
            qs = qs.filter(agencia=agencia)

        return qs

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.valuacion_terminada:
            return Response(
                {"detail": "Esta valuación ya fue terminada y no se puede editar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if instance.tecnico_finalizado and es_tecnico(request):
            return Response(
                {"detail": "La revisión técnica ya fue finalizada y no puedes editarla."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.valuacion_terminada:
            return Response(
                {"detail": "Esta valuación ya fue terminada y no se puede editar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if instance.tecnico_finalizado and es_tecnico(request):
            return Response(
                {"detail": "La revisión técnica ya fue finalizada y no puedes editarla."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="tecnico-finalizado")
    def tecnico_finalizado_action(self, request, pk=None):
        avaluo = self.get_object()

        if avaluo.valuacion_terminada:
            return Response(
                {"detail": "La valuación ya está terminada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (es_tecnico(request) or es_admin_o_valuador(request)):
            return Response(
                {"detail": "No tienes permisos para finalizar la revisión técnica."},
                status=status.HTTP_403_FORBIDDEN,
            )

        avaluo.tecnico_finalizado = True
        avaluo.fecha_tecnico_finalizado = timezone.now()
        avaluo.save(update_fields=["tecnico_finalizado", "fecha_tecnico_finalizado", "actualizado"])

        serializer = self.get_serializer(avaluo)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="valuacion-terminada")
    def valuacion_terminada_action(self, request, pk=None):
        avaluo = self.get_object()

        if not es_admin_o_valuador(request):
            return Response(
                {"detail": "No tienes permisos para marcar la valuación como terminada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        avaluo.valuacion_terminada = True
        avaluo.fecha_valuacion_terminada = timezone.now()

        if not avaluo.fecha_finalizacion:
            avaluo.fecha_finalizacion = timezone.now()

        avaluo.save(update_fields=[
            "valuacion_terminada",
            "fecha_valuacion_terminada",
            "fecha_finalizacion",
            "actualizado",
        ])

        serializer = self.get_serializer(avaluo)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="ticket-pdf")
    def ticket_pdf(self, request, pk=None):
        avaluo = self.get_object()
        return generar_ticket_pdf(avaluo)

    @action(detail=True, methods=["get"], url_path="checklist-pdf")
    def checklist_pdf(self, request, pk=None):
        avaluo = self.get_object()
        return generar_checklist_pdf(avaluo)