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
    PageBreak,
    KeepInFrame
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
    "Toldos",
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
    "Consola / tapa del compartimiento - del / tras",
    "Onstar presionar botón",
    "Onstar verificar conectividad de módulo",
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
    "Volante de direccion telescópico y de altura",
    "Claxon",
    "Limpiaparabrisas / chisgueteros / plumas",
    "Ajustes de pedales / volante",
    "Inspección visual",
    "El vehiculo cuenta con las calcomanías de la marca debajo del cofre",
    "Sistema de enfriamiento motor / radiador / mangueras",
    "Sistema de dirección",
    "Sistema eléctrico",
    "Sistema de frenos",
    "Sistema de encendido",
    "Sistema de combustible",
    "Compresor A/AC",
    "Inspección de filtros",
    "Inspección de mangueras",
    "Inspección bandas",
    "Prueba de batería",
    "Prueba de compresión / fugas / degradación de aceite motor",
    "Verificar estado de catalizador / sensores de oxígeno / emisiones",
    "Prueba de eficiencia de A/AC y carga si es necesario",
    "Visual",
    "Marco / daños",
    "Pastillas de freno / balatas",
    "Discos / pinzas / calipers / tambores",
    "Freno hidráulico",
    "Neumáticos",
    "Ruedas de acero / aleación originales segun modelo y version",
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
    "Onstar pre-activación completada",
    "Prueba de estado de salud de la batería",
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

def rutas_logos_checklist():
    rutas_base = []

    media_root = getattr(settings, "MEDIA_ROOT", "")
    base_dir = getattr(settings, "BASE_DIR", "")

    if media_root:
        rutas_base.append(str(media_root))

    if base_dir:
        rutas_base.append(os.path.join(str(base_dir), "media"))

    nombres = {
        "chevrolet": "chevrolet.png",
        "buick": "buick.png",
        "gmc": "GMC.png",
        "cadillac": "cadillac.png",
    }

    resultado = {}

    for clave, nombre_archivo in nombres.items():
        posibles = []

        for base in rutas_base:
            posibles.extend([
                os.path.join(base, nombre_archivo),
                os.path.join(base, "logos", nombre_archivo),
            ])

        for ruta in posibles:
            if os.path.exists(ruta):
                resultado[clave] = ruta
                break

    return resultado


def crear_logo_ajustado(path, max_width_cm, max_height_cm):
    if not path or not os.path.exists(path):
        return None

    img = Image(path)

    ancho_original = float(img.imageWidth)
    alto_original = float(img.imageHeight)

    if not ancho_original or not alto_original:
        return None

    max_w = max_width_cm * cm
    max_h = max_height_cm * cm

    factor = min(max_w / ancho_original, max_h / alto_original)

    img.drawWidth = ancho_original * factor
    img.drawHeight = alto_original * factor
    img.hAlign = "LEFT"

    return img


def estilos_checklist_100():
    return {
        "titulo_principal": ParagraphStyle(
            name="ChecklistTituloPrincipal",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=COLOR_NEGRO,
            alignment=TA_RIGHT,
        ),
        "subtitulo_principal": ParagraphStyle(
            name="ChecklistSubtituloPrincipal",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=COLOR_GRIS,
            alignment=TA_RIGHT,
        ),
        "mini": ParagraphStyle(
            name="ChecklistMini",
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            textColor=COLOR_GRIS,
        ),
        "mini_bold": ParagraphStyle(
            name="ChecklistMiniBold",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=COLOR_NEGRO,
        ),
        "seccion": ParagraphStyle(
            name="ChecklistSeccion",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=COLOR_ORO,
        ),
        "label": ParagraphStyle(
            name="ChecklistLabel",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=COLOR_NEGRO,
        ),
        "value": ParagraphStyle(
            name="ChecklistValue",
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            textColor=COLOR_NEGRO,
        ),
        "item": ParagraphStyle(
            name="ChecklistItem",
            fontName="Helvetica",
            fontSize=6.8,
            leading=7.8,
            textColor=COLOR_NEGRO,
        ),
        "item_bold": ParagraphStyle(
            name="ChecklistItemBold",
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=7.8,
            textColor=COLOR_NEGRO,
        ),
        "estado": ParagraphStyle(
            name="ChecklistEstado",
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=7.8,
            alignment=TA_CENTER,
            textColor=COLOR_NEGRO,
        ),
        "comentario": ParagraphStyle(
            name="ChecklistComentario",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=COLOR_NEGRO,
        ),
        "firma": ParagraphStyle(
            name="ChecklistFirma",
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
        ),
    }


def dibujar_fondo_checklist(canvas, doc):
    ancho, alto = doc.pagesize
    pagina = canvas.getPageNumber()

    canvas.saveState()

    canvas.setFillColor(COLOR_BLANCO)
    canvas.rect(0, 0, ancho, alto, stroke=0, fill=1)

    # marco exterior oro
    canvas.setStrokeColor(COLOR_ORO)
    canvas.setLineWidth(1.1)
    canvas.roundRect(
        0.32 * cm,
        0.32 * cm,
        ancho - 0.64 * cm,
        alto - 0.64 * cm,
        8,
        stroke=1,
        fill=0,
    )

    # marco interior gris
    canvas.setStrokeColor(COLOR_BORDE)
    canvas.setLineWidth(0.4)
    canvas.roundRect(
        0.42 * cm,
        0.42 * cm,
        ancho - 0.84 * cm,
        alto - 0.84 * cm,
        6,
        stroke=1,
        fill=0,
    )

    # pie
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COLOR_GRIS)
    canvas.drawRightString(ancho - 0.65 * cm, 0.55 * cm, f"Página {pagina} de 2")

    canvas.restoreState()


def barra_seccion_checklist(titulo, estilos, ancho_cm=9.7):
    t = Table(
        [[Paragraph(escape(titulo), estilos["seccion"])]],
        colWidths=[ancho_cm * cm],
    )

    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_NEGRO),
        ("BOX", (0, 0), (-1, -1), 0.3, COLOR_NEGRO),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return t


def estado_corto(valor):
    mapa = {
        "inspeccion_realizada": "INSP.",
        "requiere_servicio": "REQ.",
        "servicio_realizado": "REAL.",
        "na": "N/A",
    }
    return mapa.get(str(valor or "").strip().lower(), "—")


def estado_color(valor):
    valor = str(valor or "").strip().lower()

    if valor == "inspeccion_realizada":
        return colors.HexColor("#D1FAE5")
    if valor == "requiere_servicio":
        return colors.HexColor("#FEE2E2")
    if valor == "servicio_realizado":
        return colors.HexColor("#DBEAFE")
    if valor == "na":
        return colors.HexColor("#E5E7EB")

    return COLOR_GRIS_CLARO


def tabla_items_checklist(numeros, checklist_data, estilos, ancho_cm=9.7):
    rows = []

    for numero in numeros:
        descripcion = CHECKLIST_100[numero - 1]
        estado = checklist_data.get(str(numero), "")

        texto_item = Paragraph(
            f"<b>{numero}.</b> {escape(descripcion)}",
            estilos["item"],
        )

        texto_estado = Paragraph(
            estado_corto(estado),
            estilos["estado"],
        )

        rows.append([texto_item, texto_estado])

    t = Table(
        rows,
        colWidths=[(ancho_cm - 1.55) * cm, 1.55 * cm],
    )

    style_cmds = [
        ("BOX", (0, 0), (-1, -1), 0.35, COLOR_BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]

    for i, numero in enumerate(numeros):
        estado = checklist_data.get(str(numero), "")
        style_cmds.append(("BACKGROUND", (1, i), (1, i), estado_color(estado)))

    t.setStyle(TableStyle(style_cmds))
    return t


def header_checklist_pdf(avaluo, estilos):
    logos = rutas_logos_checklist()

    logos_flow = []

    for clave in ["buick", "chevrolet", "gmc", "cadillac"]:
        img = crear_logo_ajustado(logos.get(clave), max_width_cm=2.0, max_height_cm=0.65)
        if img:
            logos_flow.append(img)

    if logos_flow:
        tabla_logos = Table([logos_flow], colWidths=None)
        tabla_logos.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
    else:
        tabla_logos = Paragraph("SEMINUEVOS CERTIFICADOS", estilos["mini_bold"])

    bloque_izq = [
        tabla_logos,
        Spacer(1, 2),
        Paragraph("SEMINUEVOS CERTIFICADOS", estilos["mini_bold"]),
    ]

    bloque_der = [
        Paragraph("100 PUNTOS · CHECKLIST", estilos["titulo_principal"]),
        Paragraph("Valuación y Certificación de Unidades", estilos["subtitulo_principal"]),
        Spacer(1, 2),
        Paragraph(
            f"<b>Folio:</b> {obtener_id_avaluo(avaluo)} &nbsp;&nbsp;&nbsp; "
            f"<b>Fecha:</b> {escape(fecha_actual_formateada())}",
            estilos["mini_bold"],
        ),
    ]

    header = Table(
        [[bloque_izq, bloque_der]],
        colWidths=[9.5 * cm, 10.3 * cm],
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, COLOR_ORO),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return header


def tabla_datos_generales_checklist(avaluo, estilos):
    cliente = getattr(avaluo, "cliente", None)

    data = [
        [
            Paragraph("Cliente", estilos["label"]),
            Paragraph(texto(getattr(cliente, "nombre", "")), estilos["value"]),
            Paragraph("Teléfono", estilos["label"]),
            Paragraph(texto(getattr(cliente, "telefono", "")), estilos["value"]),
        ],
        [
            Paragraph("Distribuidor", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "agencia", "")), estilos["value"]),
            Paragraph("Asesor", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "asesor_ventas", "")), estilos["value"]),
        ],
        [
            Paragraph("Fecha avalúo", estilos["label"]),
            Paragraph(fmt_fecha(getattr(avaluo, "fecha_avaluo", None)), estilos["value"]),
            Paragraph("Tipo valuación", estilos["label"]),
            Paragraph(
                texto(obtener_display(avaluo, "get_tipo_valuacion_display", "tipo_valuacion")),
                estilos["value"],
            ),
        ],
        [
            Paragraph("Marca / Modelo", estilos["label"]),
            Paragraph(
                texto(f'{getattr(avaluo, "marca_auto", "")} {getattr(avaluo, "modelo", "")}'.strip()),
                estilos["value"],
            ),
            Paragraph("Versión", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "version", "")), estilos["value"]),
        ],
        [
            Paragraph("Año / KM", estilos["label"]),
            Paragraph(
                texto(f'{getattr(avaluo, "anio_modelo", "")} / {getattr(avaluo, "kilometraje", "")}'.strip(" /")),
                estilos["value"],
            ),
            Paragraph("Color", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "color", "")), estilos["value"]),
        ],
        [
            Paragraph("VIN / Serie", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "serie", "")), estilos["value"]),
            Paragraph("Placas", estilos["label"]),
            Paragraph(texto(getattr(avaluo, "placas", "")), estilos["value"]),
        ],
    ]

    t = Table(
        data,
        colWidths=[2.15 * cm, 7.05 * cm, 2.15 * cm, 8.10 * cm],
    )

    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.45, COLOR_BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ("BACKGROUND", (0, 0), (0, -1), COLOR_GRIS_CLARO),
        ("BACKGROUND", (2, 0), (2, -1), COLOR_GRIS_CLARO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return t


def columna_checklist(secciones, checklist_data, estilos):
    flowables = []

    for titulo, numeros in secciones:
        flowables.append(barra_seccion_checklist(titulo, estilos))
        flowables.append(Spacer(1, 4))
        flowables.append(tabla_items_checklist(numeros, checklist_data, estilos))
        flowables.append(Spacer(1, 8))

        if titulo == "FUNCIONAL EXTERIOR E INTERIOR":
            camaro = imagen_camaro_checklist()

            if camaro:
                flowables.append(camaro)
                flowables.append(Spacer(1, 4))

    return flowables


def bloque_dos_columnas_checklist(left_sections, right_sections, checklist_data, estilos):
    left_flow = columna_checklist(left_sections, checklist_data, estilos)
    right_flow = columna_checklist(right_sections, checklist_data, estilos)

    t = Table(
        [[left_flow, "", right_flow]],
        colWidths=[9.7 * cm, 0.3 * cm, 9.7 * cm],
    )

    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    return t


def resumen_valores_checklist(avaluo, estilos):
    data = [
        [Paragraph("Referencia / guía", estilos["label"]), Paragraph(texto(getattr(avaluo, "precio_guia", "")), estilos["value"])],
        [Paragraph("Compra Libro Azul", estilos["label"]), Paragraph(texto(getattr(avaluo, "precio_compra_libro_azul", "")), estilos["value"])],
        [Paragraph("Venta Libro Azul", estilos["label"]), Paragraph(texto(getattr(avaluo, "precio_venta_libro_azul", "")), estilos["value"])],
        [Paragraph("Total mecánica", estilos["label"]), Paragraph(moneda(getattr(avaluo, "costo_mecanica_total", 0)), estilos["value"])],
        [Paragraph("Total reparación", estilos["label"]), Paragraph(moneda(getattr(avaluo, "costo_reparacion", 0)), estilos["value"])],
        [Paragraph("Oferta inicial", estilos["label"]), Paragraph(texto(getattr(avaluo, "oferta_inicial", "")), estilos["value"])],
        [Paragraph("Oferta final", estilos["label"]), Paragraph(texto(getattr(avaluo, "oferta_final", "")), estilos["value"])],
    ]

    t = Table(data, colWidths=[4.25 * cm, 4.90 * cm])

    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.45, COLOR_BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ("BACKGROUND", (0, 0), (0, -1), COLOR_GRIS_CLARO),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return t


def caja_comentarios_checklist(avaluo, estilos):
    comentarios = recortar_texto(
        (
            getattr(avaluo, "comentarios", "")
            or getattr(avaluo, "observaciones", "")
            or getattr(avaluo, "descripcion", "")
            or "Sin comentarios."
        ),
        limite=500,
        default="Sin comentarios.",
    )

    t = Table(
        [[Paragraph(texto_pdf(comentarios), estilos["comentario"])]],
        colWidths=[9.15 * cm],
        rowHeights=[3.25 * cm],
    )

    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.45, COLOR_BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return t


def bloque_resumen_final_checklist(avaluo, estilos):
    izquierda = [
        barra_seccion_checklist("COTIZACIÓN / VALORES", estilos, ancho_cm=9.15),
        Spacer(1, 2),
        resumen_valores_checklist(avaluo, estilos),
    ]

    derecha = [
        barra_seccion_checklist("COMENTARIOS", estilos, ancho_cm=9.15),
        Spacer(1, 2),
        caja_comentarios_checklist(avaluo, estilos),
    ]

    t = Table(
        [[izquierda, "", derecha]],
        colWidths=[9.15 * cm, 0.4 * cm, 9.15 * cm],
    )

    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    return t


def firmas_checklist_mejoradas(estilos):
    firmas = Table(
        [
            ["", "", ""],
            [
                Paragraph("TÉCNICO CERTIFICADO POR GM<br/><font size='6'>Nombre y firma</font>", estilos["firma"]),
                Paragraph("GERENTE DE SEMINUEVOS<br/><font size='6'>Nombre y firma</font>", estilos["firma"]),
                Paragraph("VALUADOR - COMPRADOR<br/><font size='6'>Nombre y firma</font>", estilos["firma"]),
            ],
        ],
        colWidths=[6.1 * cm, 6.1 * cm, 6.1 * cm],
        rowHeights=[0.75 * cm, 0.75 * cm],
    )

    firmas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 1), (0, 1), 0.8, COLOR_NEGRO),
        ("LINEABOVE", (1, 1), (1, 1), 0.8, COLOR_NEGRO),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, COLOR_NEGRO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))

    return firmas

def ruta_imagen_media(nombre_archivo):
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
            os.path.join(ruta_base, nombre_archivo),
            os.path.join(ruta_base, "logos", nombre_archivo),
        ])

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta

    return None

def imagen_camaro_checklist():
    ruta = ruta_imagen_media("camaro.png")

    if not ruta:
        return None

    # Imagen original: 3800 x 900 px
    # Proporción: alto / ancho = 900 / 3800 = 0.2368
    ancho_maximo = 8.4 * cm
    alto_maximo = 1.95 * cm

    img = Image(
        ruta,
        width=ancho_maximo,
        height=alto_maximo,
        kind="proportional",
    )

    img.hAlign = "CENTER"

    contenido_seguro = KeepInFrame(
        maxWidth=9.1 * cm,
        maxHeight=2.15 * cm,
        content=[img],
        mode="shrink",
        hAlign="CENTER",
        vAlign="MIDDLE",
    )

    contenedor = Table(
        [[contenido_seguro]],
        colWidths=[9.7 * cm],
        rowHeights=[2.25 * cm],
    )

    contenedor.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.35, COLOR_BORDE),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BLANCO),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return contenedor

def generar_checklist_pdf(avaluo):
    estilos = estilos_checklist_100()
    story = []

    checklist_data = getattr(avaluo, "checklist_100", None) or {}
    if not isinstance(checklist_data, dict):
        checklist_data = {}

    # -------------------------
    # PÁGINA 1
    # -------------------------
    page1_left = [
        ("REVISIÓN EXTERIOR", list(range(1, 20))),
        ("FUNCIONAL EXTERIOR E INTERIOR", list(range(20, 24))),
    ]

    page1_right = [
        ("FUNCIONALIDAD EXTERIOR E INTERIOR", list(range(24, 39))),
        ("PRUEBA DE MANEJO", list(range(39, 58))),
    ]

    story.append(header_checklist_pdf(avaluo, estilos))
    story.append(Spacer(1, 4))
    story.append(tabla_datos_generales_checklist(avaluo, estilos))
    story.append(Spacer(1, 5))
    story.append(
        bloque_dos_columnas_checklist(
            page1_left,
            page1_right,
            checklist_data,
            estilos,
        )
    )

    # -------------------------
    # PÁGINA 2
    # -------------------------
    story.append(PageBreak())

    page2_left = [
        ("BAJO EL COFRE", list(range(58, 71))),
        ("OTRAS PRUEBAS ESPECÍFICAS", list(range(71, 74))),
        ("BAJO EL VEHÍCULO", list(range(74, 79))),
    ]

    page2_right = [
        ("BAJO EL VEHÍCULO (CONT.)", list(range(79, 90))),
        ("HISTORIAL DEL VEHÍCULO", list(range(90, 94))),
        ("CERTIFICACIÓN DEL VEHÍCULO", list(range(94, 101))),
    ]

    story.append(header_checklist_pdf(avaluo, estilos))
    story.append(Spacer(1, 4))
    story.append(
        bloque_dos_columnas_checklist(
            page2_left,
            page2_right,
            checklist_data,
            estilos,
        )
    )
    story.append(Spacer(1, 4))
    story.append(bloque_resumen_final_checklist(avaluo, estilos))
    story.append(Spacer(1, 10))
    story.append(firmas_checklist_mejoradas(estilos))

    return pdf_response(
        story,
        f"checklist_100_avaluo_{obtener_id_avaluo(avaluo)}.pdf",
        pagesize=letter,
        margin=0.50 * cm,
        on_page=dibujar_fondo_checklist,
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