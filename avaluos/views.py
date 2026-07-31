#avaluos/views.py
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


COLOR_CL_AZUL_OSCURO = colors.HexColor("#16305A")
COLOR_CL_AZUL = colors.HexColor("#2452AA")
COLOR_CL_AZUL_CLARO = colors.HexColor("#EEF3FA")
COLOR_CL_BORDE = colors.HexColor("#B7C0CC")


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
    if isinstance(valor, dict):
        valor = valor.get("estado", "")

    mapa = {
        "inspeccion_realizada": "Inspección realizada",
        "requiere_servicio": "Requiere servicio",
        "servicio_realizado": "Servicio realizado",
        "na": "N/A",
        "si": "Sí",
        "no": "No",
        "si_realizado": "Sí realizado",
        "no_realizado": "No realizado",
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

    story.append(seccion_ticket("COMENTARIOS", estilos))

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

#AQUI

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
            fontSize=17,
            leading=19,
            textColor=COLOR_NEGRO,
            alignment=TA_RIGHT,
        ),
        "subtitulo_principal": ParagraphStyle(
            name="ChecklistSubtituloPrincipal",
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            textColor=COLOR_GRIS,
            alignment=TA_RIGHT,
        ),
        "mini_bold": ParagraphStyle(
            name="ChecklistMiniBold",
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.4,
            textColor=COLOR_NEGRO,
        ),
        "seccion": ParagraphStyle(
            name="ChecklistSeccion",
            fontName="Helvetica-BoldOblique",
            fontSize=8,
            leading=10,
            textColor=COLOR_BLANCO,
        ),
        "label_top": ParagraphStyle(
            name="ChecklistLabelTop",
            fontName="Helvetica",
            fontSize=6.6,
            leading=7.6,
            alignment=TA_CENTER,
            textColor=COLOR_NEGRO,
        ),
        "sino_label": ParagraphStyle(
            name="ChecklistSiNoLabel",
            fontName="Helvetica-Bold",
            fontSize=6.6,
            leading=8,
            textColor=COLOR_NEGRO,
        ),
        "item": ParagraphStyle(
            name="ChecklistItem",
            fontName="Helvetica",
            fontSize=6.7,
            leading=7.9,
            textColor=COLOR_NEGRO,
        ),
        "col_header": ParagraphStyle(
            name="ChecklistColHeader",
            fontName="Helvetica-Bold",
            fontSize=5.2,
            leading=5.9,
            alignment=TA_CENTER,
            textColor=COLOR_NEGRO,
        ),
        "check_x": ParagraphStyle(
            name="ChecklistCheckX",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=8,
            alignment=TA_CENTER,
            textColor=COLOR_CL_AZUL,
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
        "footer": ParagraphStyle(
            name="ChecklistFooter",
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            textColor=COLOR_GRIS,
        ),
    }
 
 
def dibujar_fondo_checklist(canvas, doc):
    """Ya no dibuja el marco doble redondeado: solo el pie de página,
    igual que en el PDF de referencia (sin margen visual)."""
 
    ancho, alto = doc.pagesize
 
    canvas.saveState()
 
    canvas.setFillColor(COLOR_BLANCO)
    canvas.rect(0, 0, ancho, alto, stroke=0, fill=1)
 
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(COLOR_GRIS)
    canvas.drawString(0.65 * cm, 0.5 * cm, "EOD6.1-VCU  Rev.0")
    canvas.drawRightString(ancho - 0.65 * cm, 0.5 * cm, "Versión 2")
 
    canvas.restoreState()
 
 
def barra_seccion_checklist(titulo, estilos, ancho_cm=9.7):
    t = Table(
        [[Paragraph(escape(titulo), estilos["seccion"])]],
        colWidths=[ancho_cm * cm],
    )
 
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CL_AZUL),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
 
    return t
 
 
def estado_desde_valor_checklist(valor):
    if isinstance(valor, dict):
        return str(valor.get("estado") or "").strip().lower()
 
    return str(valor or "").strip().lower()
 
 
def fecha_desde_valor_checklist(valor):
    if isinstance(valor, dict):
        return str(valor.get("fecha") or "").strip()
 
    return str(valor or "").strip()
 
 
def medida_desde_valor_checklist(valor, campo):
    if not isinstance(valor, dict):
        return ""
 
    return str(valor.get(campo) or "").strip()
 
 
def valor_checklist(checklist_data, numero):
    return checklist_data.get(str(numero), "")
 
 
# Grupos de columnas (checkbox) según el tipo de ítem
COLUMNAS_DEFAULT = [
    ("INSPECCIÓN\nREALIZADA", "inspeccion_realizada"),
    ("REQUIERE\nSERVICIO", "requiere_servicio"),
    ("SERVICIO\nREALIZADO", "servicio_realizado"),
    ("N/A", "na"),
]
 
COLUMNAS_HISTORIAL = [
    ("SI", "si"),
    ("NO", "no"),
    ("N/A", "na"),
]
 
COLUMNAS_CERTIFICACION = [
    ("SI\nREALIZADO", "si_realizado"),
    ("NO\nREALIZADO", "no_realizado"),
    ("N/A", "na"),
]
 
 
def columnas_para_numero(numero):
    if 90 <= numero <= 92:
        return COLUMNAS_HISTORIAL
    if 94 <= numero <= 100:
        return COLUMNAS_CERTIFICACION
    return COLUMNAS_DEFAULT
 
 
ANCHO_BLOQUE_CHECKS_CM = 4.0
 
 
def casilla_si_no(estilos):
    """Casilla vacía SI / NO para los campos nuevos (Manual de Garantía,
    Compra Directa, Toma a Cuenta, Garantía Vigente). Siempre se muestran
    vacías porque todavía no existe el dato real en el modelo."""
 
    t = Table(
        [[
            Paragraph("SI", estilos["sino_label"]),
            "",
            Paragraph("NO", estilos["sino_label"]),
            "",
        ]],
        colWidths=[0.42 * cm, 0.34 * cm, 0.46 * cm, 0.34 * cm],
        rowHeights=[0.34 * cm],
    )
    t.setStyle(TableStyle([
        ("BOX", (1, 0), (1, 0), 0.4, COLOR_CL_BORDE),
        ("BOX", (3, 0), (3, 0), 0.4, COLOR_CL_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t
 
 
def descripcion_item_checklist(numero, descripcion, valor):
    if numero == 93:
        fecha = fecha_desde_valor_checklist(valor)
        extra = f"<br/><b>Fecha:</b> {escape(fecha)}" if fecha else "<br/><b>Fecha:</b> __________"
        return f"<b>{numero}.-</b> {escape(descripcion)}{extra}"
 
    if numero in (76, 79):
        dd = medida_desde_valor_checklist(valor, "dd")
        id_ = medida_desde_valor_checklist(valor, "id")
        it = medida_desde_valor_checklist(valor, "it")
        dt = medida_desde_valor_checklist(valor, "dt")
 
        extra = (
            "<br/><b>De espesor:</b> "
            f"DD {escape(dd) or '____'} &nbsp;&nbsp; "
            f"ID {escape(id_) or '____'} &nbsp;&nbsp; "
            f"IT {escape(it) or '____'} &nbsp;&nbsp; "
            f"DT {escape(dt) or '____'} mm"
        )
 
        return f"<b>{numero}.-</b> {escape(descripcion)}{extra}"
 
    return f"<b>{numero}.-</b> {escape(descripcion)}"
 
 
def encabezado_columnas_checklist(columnas, estilos, ancho_desc_cm, ancho_total_cm=ANCHO_BLOQUE_CHECKS_CM):
    n_cols = len(columnas)
    ancho_check = ancho_total_cm / n_cols
 
    fila = [""]
    for etiqueta, _clave in columnas:
        fila.append(Paragraph(etiqueta.replace("\n", "<br/>"), estilos["col_header"]))
 
    t = Table([fila], colWidths=[ancho_desc_cm * cm] + [ancho_check * cm] * n_cols)
    t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t
 
 
def fila_item_checklist(numero, checklist_data, estilos, ancho_desc_cm, ancho_total_cm=ANCHO_BLOQUE_CHECKS_CM):
    descripcion = CHECKLIST_100[numero - 1]
    valor = valor_checklist(checklist_data, numero)
    estado_activo = estado_desde_valor_checklist(valor)
 
    columnas = columnas_para_numero(numero)
    n_cols = len(columnas)
    ancho_check = ancho_total_cm / n_cols
 
    fila = [Paragraph(descripcion_item_checklist(numero, descripcion, valor), estilos["item"])]
 
    for _etiqueta, clave in columnas:
        marca = "X" if estado_activo == clave else ""
        caja = Table(
            [[Paragraph(marca, estilos["check_x"])]],
            colWidths=[0.34 * cm],
            rowHeights=[0.32 * cm],
        )
        caja.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.35, COLOR_CL_BORDE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
 
        envoltura = Table([[caja]], colWidths=[ancho_check * cm])
        envoltura.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        fila.append(envoltura)
 
    t = Table(
        [fila],
        colWidths=[ancho_desc_cm * cm] + [ancho_check * cm] * n_cols,
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
    ]))
    return t
 
 
def header_checklist_pdf(avaluo, estilos):
    logos = rutas_logos_checklist()
 
    logos_flow = []
 
    for clave in ["chevrolet", "buick", "gmc", "cadillac"]:
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
        Paragraph("100 Puntos, Check List", estilos["titulo_principal"]),
        Paragraph("de Valuación y Certificación de Unidades", estilos["subtitulo_principal"]),
    ]
 
    header = Table(
        [[bloque_izq, bloque_der]],
        colWidths=[9.5 * cm, 10.3 * cm],
    )
 
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, COLOR_CL_AZUL),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
 
    return header
 
 
def celda_dato_checklist(etiqueta, ancho_cm, estilos, alto_valor_cm=0.55):
    """Cajita con la etiqueta arriba (fondo azul clarito) y el espacio en
    blanco para llenar a mano abajo, tal cual el PDF de referencia."""
 
    etiqueta_tbl = Table(
        [[Paragraph(escape(etiqueta), estilos["label_top"])]],
        colWidths=[ancho_cm * cm],
        rowHeights=[0.42 * cm],
    )
    etiqueta_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, COLOR_CL_BORDE),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CL_AZUL_CLARO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
 
    valor_tbl = Table(
        [[""]],
        colWidths=[ancho_cm * cm],
        rowHeights=[alto_valor_cm * cm],
    )
    valor_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, COLOR_CL_BORDE),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BLANCO),
    ]))
 
    contenedor = Table([[etiqueta_tbl], [valor_tbl]], colWidths=[ancho_cm * cm])
    contenedor.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return contenedor
 
 
def fila_datos_generales_checklist(campos, estilos):
    celdas = [celda_dato_checklist(etiqueta, ancho, estilos) for etiqueta, ancho in campos]
 
    t = Table([celdas])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t
 
 
def tabla_datos_generales_checklist(avaluo, estilos):
    cliente = getattr(avaluo, "cliente", None)
 
    fila1 = fila_datos_generales_checklist([
        ("Nombre del cliente", 8.5),
        ("Teléfono", 4.7),
        ("Distribuidor", 5.9),
    ], estilos)
 
    fila2 = fila_datos_generales_checklist([
        ("Fecha de Valuación", 4.0),
        ("VIN", 4.0),
        ("Marca", 2.4),
        ("Versión", 2.4),
        ("Año", 1.8),
        ("Kms.", 2.3),
        ("Color", 2.2),
    ], estilos)
 
    # Los valores se muestran arriba de la celda blanca, como pequeña
    # referencia impresa; el espacio en blanco de abajo queda para llenar
    # a mano igual que en el PDF de referencia.
    valores = Table(
        [[
            Paragraph(texto(getattr(cliente, "nombre", "")), estilos["item"]),
            Paragraph(texto(getattr(cliente, "telefono", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "agencia", "")), estilos["item"]),
        ]],
        colWidths=[8.5 * cm, 4.7 * cm, 5.9 * cm],
    )
    valores.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
 
    valores2 = Table(
        [[
            Paragraph(fmt_fecha(getattr(avaluo, "fecha_avaluo", None)), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "serie", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "marca_auto", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "version", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "anio_modelo", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "kilometraje", "")), estilos["item"]),
            Paragraph(texto(getattr(avaluo, "color", "")), estilos["item"]),
        ]],
        colWidths=[4.0 * cm, 4.0 * cm, 2.4 * cm, 2.4 * cm, 1.8 * cm, 2.3 * cm, 2.2 * cm],
    )
    valores2.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
 
    # Superponemos los valores dentro del renglón en blanco: se logra
    # colocando la tabla de valores inmediatamente después, con margen
    # negativo simulado mediante un Spacer mínimo (ReportLab no permite
    # overlay real de flowables, así que el valor va debajo del renglón
    # de captura, a manera de referencia impresa).
    return [fila1, Spacer(1, 2), valores, Spacer(1, 3), fila2, Spacer(1, 2), valores2]
 
 
def fila_campos_extra_checklist(estilos):
    """Fila con Manual de Garantía, Compra Directa, Toma a Cuenta,
    Garantía Vigente y Placa. Los SI/NO se muestran vacíos porque todavía
    no hay un campo real en el modelo para guardarlos."""
 
    campos = [
        ("Manual de Garantía", 3.9),
        ("Compra Directa", 3.4),
        ("Toma a Cuenta", 3.4),
        ("Garantia Vigente", 3.6),
    ]
 
    celdas = []
    anchos = []
 
    for etiqueta, ancho in campos:
        fila = Table(
            [[Paragraph(escape(etiqueta), estilos["sino_label"]), casilla_si_no(estilos)]],
            colWidths=[(ancho - 1.6) * cm, 1.6 * cm],
        )
        fila.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        celdas.append(fila)
        anchos.append(ancho * cm)
 
    placa = Table(
        [[
            Paragraph("Placa", estilos["sino_label"]),
            Table([[""]], colWidths=[3.2 * cm], rowHeights=[0.4 * cm],
                  style=TableStyle([("BOX", (0, 0), (-1, -1), 0.4, COLOR_CL_BORDE)])),
        ]],
        colWidths=[1.5 * cm, 3.2 * cm],
    )
    placa.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    celdas.append(placa)
    anchos.append(4.7 * cm)
 
    t = Table([celdas], colWidths=anchos)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, COLOR_CL_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t
 
 
def seccion_checklist(titulo, numeros, checklist_data, estilos, ancho_cm=9.7, mostrar_header=False):
    """Devuelve la lista de flowables de una sección: barra de título,
    encabezado de columnas opcional (solo si cambia el tipo de columnas
    respecto a la sección anterior) y los renglones de cada ítem."""
 
    ancho_desc = ancho_cm - ANCHO_BLOQUE_CHECKS_CM
 
    flow = [barra_seccion_checklist(titulo, estilos, ancho_cm)]
 
    if mostrar_header:
        flow.append(Spacer(1, 1))
        flow.append(encabezado_columnas_checklist(
            columnas_para_numero(numeros[0]), estilos, ancho_desc,
        ))
 
    for numero in numeros:
        flow.append(fila_item_checklist(numero, checklist_data, estilos, ancho_desc))
 
    return flow
 
 
def columna_checklist(secciones, checklist_data, estilos):
    """secciones: lista de tuplas (titulo, numeros). Se imprime el
    encabezado de columnas solo en la primera sección y cada vez que
    cambia el tipo de columnas (default / historial / certificación),
    igual que en el PDF de referencia."""
 
    flowables = []
    tipo_anterior = None
 
    for index, (titulo, numeros) in enumerate(secciones):
        if index > 0:
            flowables.append(Spacer(1, 12))
 
        tipo_actual = columnas_para_numero(numeros[0])
        mostrar_header = tipo_actual is not tipo_anterior
        tipo_anterior = tipo_actual
 
        flowables += seccion_checklist(titulo, numeros, checklist_data, estilos, mostrar_header=mostrar_header)
 
        if titulo == "FUNCIONAL EXTERIOR E INTERIOR":
            camaro = imagen_camaro_checklist()
 
            if camaro:
                flowables.append(Spacer(1, 10))
                flowables.append(camaro)
 
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
    filas = [
        ("Referencia libro:", ""),
        ("Toma:", moneda(getattr(avaluo, "precio_compra_libro_azul", 0)) if getattr(avaluo, "precio_compra_libro_azul", None) else texto(getattr(avaluo, "precio_compra_libro_azul", ""))),
        ("Venta:", texto(getattr(avaluo, "precio_venta_libro_azul", ""))),
        ("Reacondicionamiento:", ""),
        ("Mano de obra:", moneda(getattr(avaluo, "costo_mecanica_total", 0))),
        ("Partes / refacciones:", moneda(getattr(avaluo, "costo_reparacion", 0))),
        ("HyP:", ""),
        ("Total:", moneda(getattr(avaluo, "costo_estimado", 0))),
        ("Valor toma:", texto(getattr(avaluo, "oferta_inicial", ""))),
        ("Oferta final:", texto(getattr(avaluo, "oferta_final", ""))),
    ]
 
    data = [[Paragraph(f"<b>{escape(etq)}</b> {escape(val)}", estilos["comentario"])] for etq, val in filas]
 
    t = Table(data, colWidths=[9.15 * cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
 
    return t
 
 
def caja_comentarios_checklist(avaluo, estilos):
    comentarios = recortar_texto(
        (
            getattr(avaluo, "comentarios_checklist", "")
            or "Sin comentarios técnicos."
        ),
        limite=500,
        default="Sin comentarios técnicos.",
    )
 
    t = Table(
        [[Paragraph(texto_pdf(comentarios), estilos["comentario"])]],
        colWidths=[9.15 * cm],
        rowHeights=[3.25 * cm],
    )
 
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, COLOR_CL_BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
 
    return t
 
 
def bloque_resumen_final_checklist(avaluo, estilos):
    izquierda = [
        barra_seccion_checklist("COTIZACIÓN", estilos, ancho_cm=9.15),
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
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
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
    story.append(Spacer(1, 6))
    story += tabla_datos_generales_checklist(avaluo, estilos)
    story.append(Spacer(1, 2))
    story.append(fila_campos_extra_checklist(estilos))
    story.append(Spacer(1, 10))
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
    story.append(Spacer(1, 15))
    story.append(
        bloque_dos_columnas_checklist(
            page2_left,
            page2_right,
            checklist_data,
            estilos,
        )
    )
    story.append(Spacer(1, 6))
    story.append(bloque_resumen_final_checklist(avaluo, estilos))
    story.append(Spacer(1, 10))
    story.append(firmas_checklist_mejoradas(estilos))
 
    return pdf_response(
        story,
        f"checklist_100_avaluo_{obtener_id_avaluo(avaluo)}.pdf",
        pagesize=letter,
        margin=0.45 * cm,
        on_page=dibujar_fondo_checklist,
    )

#AQUI

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