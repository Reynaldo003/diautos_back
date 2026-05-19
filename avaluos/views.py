import os
from io import BytesIO
from decimal import Decimal
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)

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


COLOR_ORO = colors.HexColor("#C9A75D")
COLOR_NEGRO = colors.HexColor("#111827")
COLOR_GRIS = colors.HexColor("#475569")
COLOR_GRIS_CLARO = colors.HexColor("#F8FAFC")
COLOR_BORDE = colors.HexColor("#CBD5E1")
COLOR_BLANCO = colors.white

# Media carta horizontal: 8.5 x 5.5 pulgadas.
MEDIA_CARTA_HORIZONTAL = (letter[0], letter[1] / 2)


def normalizar_rol(request):
    rol = getattr(request.user, "rol", "") or ""
    return str(rol).strip().lower()


def es_admin_o_valuador(request):
    rol = normalizar_rol(request)
    permisos = getattr(request.user, "permisos", []) or []
    permisos_normalizados = [str(p).lower() for p in permisos]

    return (
        "administrador" in rol
        or "valuador" in rol
        or "all" in permisos_normalizados
        or "usuarios_admin" in permisos_normalizados
    )


def es_tecnico(request):
    rol = normalizar_rol(request)
    return "tecnico" in rol or "técnico" in rol


def formatear_fecha_segura(valor):
    if not valor:
        return "—"

    try:
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)

        return valor.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def fecha_actual_formateada():
    ahora = timezone.now()

    try:
        if timezone.is_aware(ahora):
            ahora = timezone.localtime(ahora)

        return ahora.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(ahora)


def fmt_fecha(valor):
    return formatear_fecha_segura(valor)


def texto(valor, default="—"):
    valor = "" if valor is None else str(valor).strip()
    return valor or default


def texto_pdf(valor, default="—"):
    valor = texto(valor, default)
    return escape(valor).replace("\n", "<br/>")


def parrafo_pdf(valor, estilo, default="—"):
    return Paragraph(texto_pdf(valor, default), estilo)


def recortar_texto(valor, limite=260, default="—"):
    valor = texto(valor, default)

    if len(valor) <= limite:
        return valor

    return valor[:limite].rstrip() + "..."


def moneda(valor):
    try:
        numero = Decimal(str(valor or "0"))
    except Exception:
        numero = Decimal("0")

    return f"${numero:,.2f}"


def obtener_id_avaluo(avaluo):
    return getattr(avaluo, "id", "sin_id")


def obtener_display(objeto, nombre_metodo, nombre_campo):
    metodo = getattr(objeto, nombre_metodo, None)

    if callable(metodo):
        try:
            return metodo()
        except Exception:
            pass

    return getattr(objeto, nombre_campo, "")


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


def pdf_response(story, filename, pagesize=letter, margin=1.2 * cm, on_page=None):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    if on_page:
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    else:
        doc.build(story)

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def ruta_logo_seminuevos():
    rutas_base = []

    media_root = getattr(settings, "MEDIA_ROOT", "")
    base_dir = getattr(settings, "BASE_DIR", "")

    if media_root:
        rutas_base.append(str(media_root))

    if base_dir:
        rutas_base.append(os.path.join(str(base_dir), "media"))

    posibles_rutas = []

    for ruta_base in rutas_base:
        posibles_rutas.extend([
            os.path.join(ruta_base, "seminuevos.png"),
            os.path.join(ruta_base, "logos", "seminuevos.png"),
        ])

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta

    return None


def estilos_ticket():
    return {
        "titulo": ParagraphStyle(
            name="TicketTitulo",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            name="TicketSubtitulo",
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=12,
            textColor=COLOR_GRIS,
            alignment=TA_CENTER,
        ),
        "fecha": ParagraphStyle(
            name="TicketFecha",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=COLOR_NEGRO,
            alignment=TA_RIGHT,
        ),
        "logo_texto": ParagraphStyle(
            name="TicketLogoTexto",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=COLOR_NEGRO,
            alignment=TA_RIGHT,
        ),
        "seccion": ParagraphStyle(
            name="TicketSeccion",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=COLOR_ORO,
            alignment=TA_LEFT,
        ),
        "etiqueta": ParagraphStyle(
            name="TicketEtiqueta",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=COLOR_NEGRO,
        ),
        "valor": ParagraphStyle(
            name="TicketValor",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=COLOR_NEGRO,
        ),
        "comentario": ParagraphStyle(
            name="TicketComentario",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=COLOR_NEGRO,
        ),
        "firma": ParagraphStyle(
            name="TicketFirma",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
        ),
    }


def dibujar_fondo_ticket(canvas, doc):
    ancho, alto = doc.pagesize

    canvas.saveState()

    canvas.setFillColor(COLOR_BLANCO)
    canvas.rect(0, 0, ancho, alto, stroke=0, fill=1)

    canvas.setStrokeColor(COLOR_ORO)
    canvas.setLineWidth(1.4)
    canvas.roundRect(
        0.35 * cm,
        0.35 * cm,
        ancho - 0.70 * cm,
        alto - 0.70 * cm,
        8,
        stroke=1,
        fill=0,
    )

    canvas.setStrokeColor(COLOR_BORDE)
    canvas.setLineWidth(0.4)
    canvas.roundRect(
        0.45 * cm,
        0.45 * cm,
        ancho - 0.90 * cm,
        alto - 0.90 * cm,
        6,
        stroke=1,
        fill=0,
    )

    canvas.restoreState()


def seccion_ticket(titulo, estilos):
    t = Table(
        [[Paragraph(escape(titulo), estilos["seccion"])]],
        colWidths=[20 * cm],
    )

    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_NEGRO),
        ("BOX", (0, 0), (-1, -1), 0.3, COLOR_NEGRO),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return t


def tabla_datos_ticket(filas, estilos):
    data = []

    for etiqueta_1, valor_1, etiqueta_2, valor_2 in filas:
        data.append([
            parrafo_pdf(etiqueta_1, estilos["etiqueta"]),
            parrafo_pdf(valor_1, estilos["valor"]),
            parrafo_pdf(etiqueta_2, estilos["etiqueta"]),
            parrafo_pdf(valor_2, estilos["valor"]),
        ])

    t = Table(
        data,
        colWidths=[2.55 * cm, 6.95 * cm, 2.85 * cm, 7.65 * cm],
    )

    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COLOR_BORDE),

        ("BACKGROUND", (0, 0), (0, -1), COLOR_GRIS_CLARO),
        ("BACKGROUND", (2, 0), (2, -1), COLOR_GRIS_CLARO),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return t


def generar_ticket_pdf(avaluo):
    estilos = estilos_ticket()
    story = []

    logo_path = ruta_logo_seminuevos()

    titulo = Paragraph(
        "SOLICITUD DE SERVICIO &amp;<br/>REFACCIONES",
        estilos["titulo"],
    )

    subtitulo = Paragraph("Cargo Interno", estilos["subtitulo"])

    encabezado_izquierdo = [
        titulo,
        Spacer(1, 2),
        subtitulo,
    ]

    if logo_path:
        logo = Image(logo_path)
        alto_logo = 1.15 * cm
        proporcion_logo = 501 / 131

        logo.drawHeight = alto_logo
        logo.drawWidth = alto_logo * proporcion_logo

        logo.hAlign = "RIGHT"

        encabezado_derecho = [
            logo,
            Spacer(1, 1),
            Paragraph(
                f"<b>FECHA:</b> {escape(fecha_actual_formateada())}",
                estilos["fecha"],
            ),
        ]
    else:
        encabezado_derecho = [
            Paragraph(
                "CHEVROLET<br/>SEMINUEVOS CERTIFICADOS",
                estilos["logo_texto"],
            ),
            Spacer(1, 3),
            Paragraph(
                f"<b>FECHA:</b> {escape(fecha_actual_formateada())}",
                estilos["fecha"],
            ),
        ]

    header = Table(
        [[encabezado_izquierdo, encabezado_derecho]],
        colWidths=[9 * cm, 11 * cm],
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, COLOR_ORO),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story.append(header)
    story.append(Spacer(1, 3))

    story.append(seccion_ticket("DATOS DE LA SOLICITUD", estilos))

    story.append(tabla_datos_ticket([
        [
            "Folio",
            obtener_id_avaluo(avaluo),
            "Generado",
            fecha_actual_formateada(),
        ],
        [
            "Asesor",
            getattr(avaluo, "asesor_ventas", ""),
            "Agencia",
            getattr(avaluo, "agencia", ""),
        ],
    ], estilos))

    story.append(Spacer(1, 3))

    story.append(seccion_ticket("DATOS DEL VEHÍCULO", estilos))

    story.append(tabla_datos_ticket([
        [
            "Marca",
            getattr(avaluo, "marca_auto", ""),
            "Color",
            getattr(avaluo, "color", ""),
        ],
        [
            "Modelo",
            getattr(avaluo, "modelo", ""),
            "Año",
            getattr(avaluo, "anio_modelo", ""),
        ],
        [
            "Versión",
            getattr(avaluo, "version", ""),
            "No. Serie",
            getattr(avaluo, "serie", ""),
        ],
        [
            "Vendedor",
            getattr(avaluo, "vendedor", "") or getattr(avaluo, "asesor_ventas", ""),
            "Placas",
            getattr(avaluo, "placas", ""),
        ],
        [
            "KM",
            getattr(avaluo, "kilometraje", ""),
            "Fecha avalúo",
            fmt_fecha(getattr(avaluo, "fecha_avaluo", None)),
        ],
    ], estilos))

    story.append(Spacer(1, 3))

    story.append(seccion_ticket("COMENTARIOS / TRABAJO SOLICITADO", estilos))

    comentarios = (
        getattr(avaluo, "comentarios", "")
        or getattr(avaluo, "observaciones", "")
        or "Valuación"
    )

    comentarios = recortar_texto(comentarios, limite=260, default="Valuación")

    tabla_comentarios = Table(
        [[parrafo_pdf(comentarios, estilos["comentario"])]],
        colWidths=[20 * cm],
        rowHeights=[1.45 * cm],
    )

    tabla_comentarios.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tabla_comentarios)
    story.append(Spacer(1, 4))

    firmas = Table(
        [
            ["", ""],
            [
                Paragraph(
                    "RESPONSABLE DE SOLICITUD<br/><font size='6'>Nombre y firma</font>",
                    estilos["firma"],
                ),
                Paragraph(
                    "RESPONSABLE DE AUTORIZACIÓN<br/><font size='6'>Nombre y firma</font>",
                    estilos["firma"],
                ),
            ],
        ],
        colWidths=[9.6 * cm, 9.6 * cm],
        rowHeights=[0.8 * cm, 0.65 * cm],
    )

    firmas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LINEABOVE", (0, 1), (0, 1), 0.8, COLOR_NEGRO),
        ("LINEABOVE", (1, 1), (1, 1), 0.8, COLOR_NEGRO),

        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))

    story.append(firmas)

    return pdf_response(
        story,
        f"ticket_avaluo_{obtener_id_avaluo(avaluo)}.pdf",
        pagesize=MEDIA_CARTA_HORIZONTAL,
        margin=0.45 * cm,
        on_page=dibujar_fondo_ticket,
    )


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


def generar_checklist_pdf(avaluo):
    styles = getSampleStyleSheet()
    story = []

    cliente = getattr(avaluo, "cliente", None)

    story.append(Paragraph("100 Puntos Checklist", styles["Title"]))
    story.append(Paragraph("de Valuación y Certificación de Unidad", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos generales", styles["Heading2"]))

    story.append(tabla_datos_ticket([
        ["Campo", "Valor", "Campo", "Valor"],
        [
            "Cliente",
            texto(getattr(cliente, "nombre", "")),
            "Teléfono",
            texto(getattr(cliente, "telefono", "")),
        ],
        [
            "Correo",
            texto(getattr(cliente, "correo", "")),
            "Agencia",
            texto(getattr(avaluo, "agencia", "")),
        ],
        [
            "Asesor",
            texto(getattr(avaluo, "asesor_ventas", "")),
            "Fecha avalúo",
            fmt_fecha(getattr(avaluo, "fecha_avaluo", None)),
        ],
        [
            "Tipo valuación",
            texto(obtener_display(avaluo, "get_tipo_valuacion_display", "tipo_valuacion")),
            "Tipo toma",
            texto(obtener_display(avaluo, "get_tipo_toma_display", "tipo_toma")),
        ],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos del coche", styles["Heading2"]))

    story.append(tabla([
        ["Campo", "Valor", "Campo", "Valor"],
        [
            "Marca",
            texto(getattr(avaluo, "marca_auto", "")),
            "Modelo",
            texto(getattr(avaluo, "modelo", "")),
        ],
        [
            "Año",
            texto(getattr(avaluo, "anio_modelo", "")),
            "Versión",
            texto(getattr(avaluo, "version", "")),
        ],
        [
            "No. Serie",
            texto(getattr(avaluo, "serie", "")),
            "Placas",
            texto(getattr(avaluo, "placas", "")),
        ],
        [
            "Color",
            texto(getattr(avaluo, "color", "")),
            "KM",
            texto(getattr(avaluo, "kilometraje", "")),
        ],
    ], [3.2 * cm, 6 * cm, 4 * cm, 6 * cm]))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Checklist 100 puntos", styles["Heading2"]))

    checklist = getattr(avaluo, "checklist_100", None) or {}

    if not isinstance(checklist, dict):
        checklist = {}

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
        ["Mecánica", moneda(getattr(avaluo, "costo_mecanica_total", 0))],
        ["Total reparación", moneda(getattr(avaluo, "costo_reparacion", 0))],
        ["Oferta inicial", texto(getattr(avaluo, "oferta_inicial", ""))],
        ["Oferta final", texto(getattr(avaluo, "oferta_final", ""))],
    ], [8 * cm, 8 * cm]))

    story.append(Spacer(1, 25))

    story.append(tabla([
        ["Responsable de solicitud", "Responsable de autorización", "Valuador - Comprador"],
        ["\n\nNombre y firma", "\n\nNombre y firma", "\n\nNombre y firma"],
    ], [6 * cm, 6 * cm, 6 * cm]))

    return pdf_response(
        story,
        f"checklist_100_avaluo_{obtener_id_avaluo(avaluo)}.pdf",
    )


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
        avaluo.save(update_fields=[
            "tecnico_finalizado",
            "fecha_tecnico_finalizado",
            "actualizado",
        ])

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