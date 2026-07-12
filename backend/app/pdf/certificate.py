from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from app.core.config import BACKEND_DIR
from app.models import Certificate, TechnicalSignatory


CERTIFICATE_DIR = BACKEND_DIR / "data" / "certificates"
CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)
LOGO_PATH = BACKEND_DIR / "app" / "pdf" / "assets" / "fnlifting-certificate-logo.png"

INK = colors.HexColor("#151515")
LINE = colors.HexColor("#303030")
HEADER = colors.HexColor("#C9C9C9")
BRAND_BLUE = colors.HexColor("#1761A7")
WATERMARK = colors.HexColor("#E1F4F8")


def _fmt(value) -> str:
    return value.strftime("%d/%b/%Y") if value else "—"


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, height: float, *, size: float = 6.2,
               bold: bool = False, align: int = 0, leading: float | None = None) -> None:
    style = ParagraphStyle(
        "certificate-cell",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size * 1.17,
        textColor=INK,
        alignment=align,
        spaceAfter=0,
        spaceBefore=0,
    )
    paragraph = Paragraph((text or "—").replace("\n", "<br/>"), style)
    paragraph.wrapOn(canvas, width, height)
    paragraph.drawOn(canvas, x, y + max(0, (height - paragraph.height) / 2))


def _cell(canvas: Canvas, x: float, y: float, width: float, height: float, text: str = "", *,
          fill=None, size: float = 6, bold: bool = False, align: int = 1, padding: float = 1.2 * mm) -> None:
    if fill:
        canvas.setFillColor(fill)
        canvas.rect(x, y, width, height, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.35)
    canvas.rect(x, y, width, height, fill=0, stroke=1)
    if text:
        _paragraph(canvas, text, x + padding, y + 0.8 * mm, width - padding * 2, height - 1.6 * mm,
                   size=size, bold=bold, align=align)


def _draw_qr(canvas: Canvas, value: str, x: float, y: float, size: float) -> None:
    qr = QrCodeWidget(value)
    x1, y1, x2, y2 = qr.getBounds()
    drawing = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    drawing.add(qr)
    renderPDF.draw(drawing, canvas, x, y)


def _draw_watermark(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(WATERMARK)
    canvas.setStrokeColor(WATERMARK)
    canvas.setLineWidth(8 * mm)
    canvas.line(31 * mm, 266 * mm, 168 * mm, 102 * mm)
    canvas.line(43 * mm, 266 * mm, 189 * mm, 119 * mm)
    canvas.circle(45 * mm, 161 * mm, 25 * mm, fill=0, stroke=1)
    canvas.circle(164 * mm, 139 * mm, 22 * mm, fill=0, stroke=1)
    canvas.setLineWidth(4 * mm)
    canvas.line(9 * mm, 166 * mm, 48 * mm, 189 * mm)
    canvas.line(165 * mm, 158 * mm, 207 * mm, 142 * mm)
    canvas.restoreState()


def _draw_signatory_asset(canvas: Canvas, signatory: TechnicalSignatory | None, x: float, y: float,
                          width: float, height: float) -> None:
    if not signatory:
        return
    signature = Path(signatory.signature_path) if signatory.signature_path else None
    stamp = Path(signatory.stamp_path) if signatory.stamp_path else None
    if signature and signature.exists() and stamp and signature.resolve() == stamp.resolve():
        canvas.drawImage(str(signature), x, y, width, height, preserveAspectRatio=True, mask="auto", anchor="c")
        return
    if signature and signature.exists():
        canvas.drawImage(str(signature), x, y + height * 0.05, width * 0.72, height * 0.72,
                         preserveAspectRatio=True, mask="auto", anchor="c")
    if stamp and stamp.exists():
        canvas.drawImage(str(stamp), x + width * 0.56, y, width * 0.42, height,
                         preserveAspectRatio=True, mask="auto", anchor="c")


def _draw_header(canvas: Canvas, certificate: Certificate) -> None:
    page_width, page_height = A4
    if LOGO_PATH.exists():
        canvas.drawImage(str(LOGO_PATH), 7 * mm, page_height - 29 * mm, 31 * mm, 22 * mm,
                         preserveAspectRatio=True, mask="auto", anchor="c")
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 9.2)
    canvas.drawCentredString(page_width / 2, page_height - 23 * mm, "Certificate Of Thorough Examination")
    canvas.setFont("Helvetica-Bold", 6.5)
    canvas.drawCentredString(page_width / 2, page_height - 29 * mm,
                             "This certificate meets the Lifting Equipment Engineers Association Technical requirements")
    canvas.setFont("Helvetica", 5.7)
    canvas.drawRightString(page_width - 7 * mm, page_height - 17 * mm,
                           certificate.service_order_no or "SERVICE ORDER—")


def generate_certificate_pdf(certificate: Certificate) -> Path:
    inspection = certificate.inspection
    equipment = certificate.equipment
    client = certificate.client
    inspector_profile = inspection.inspector.technical_signatory if inspection.inspector else None
    approver = certificate.approver_signatory
    output = CERTIFICATE_DIR / f"{certificate.certificate_no.replace('/', '-')}.pdf"
    canvas = Canvas(str(output), pagesize=A4, pageCompression=1)
    page_width, page_height = A4
    canvas.setTitle(certificate.certificate_no)
    canvas.setAuthor("FNLIFTING ANGOLA")
    _draw_watermark(canvas)
    _draw_header(canvas, certificate)

    left = 8 * mm
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(left, page_height - 48 * mm, f"Company Name & Address: {client.name.upper()} — {client.address or 'Address not provided'}")
    canvas.drawString(left, page_height - 56 * mm, f"Report No: {certificate.report_no or certificate.certificate_no}")
    canvas.drawString(66 * mm, page_height - 56 * mm, f"Identification No: {certificate.identification_no or 'See below'}")
    canvas.drawString(117 * mm, page_height - 56 * mm, f"Date of Report: {_fmt(certificate.issued_at)}")
    canvas.drawString(left, page_height - 64 * mm, f"Inspected in accordance with: {certificate.standard_reference}")
    canvas.drawString(159 * mm, page_height - 48 * mm, f"Phone: {client.phone or '—'}")
    canvas.drawString(166 * mm, page_height - 56 * mm, f"Colour code: {certificate.colour_code or '—'}")

    table_x = 4 * mm
    table_w = page_width - 8 * mm
    top = 213 * mm
    header_block_h = 23 * mm
    left_w, middle_w = 103 * mm, 62 * mm
    _cell(canvas, table_x, top - header_block_h, left_w, header_block_h, align=0)
    _paragraph(canvas,
               "Name of the Inspector and Address of employer for whom the thorough examination was made<br/>"
               f"<b>{inspection.inspector.full_name if inspection.inspector else 'FNLIFTING Technical Team'} / "
               f"{inspector_profile.employer_name if inspector_profile else 'FNLIFTING ANGOLA'}</b>",
               table_x + 1.5 * mm, top - header_block_h + 1.2 * mm, left_w - 3 * mm, header_block_h - 2.4 * mm,
               size=6.4, align=0)
    _cell(canvas, table_x + left_w, top - header_block_h, middle_w, header_block_h, align=0)
    _paragraph(canvas,
               "Address of the premises at which the examination was made:<br/>"
               f"<b>{inspection.location or equipment.location or client.address or '—'}</b>",
               table_x + left_w + 1.5 * mm, top - header_block_h + 1.2 * mm, middle_w - 3 * mm,
               header_block_h - 2.4 * mm, size=6.4, align=0)
    status_w = table_w - left_w - middle_w
    _cell(canvas, table_x + left_w + middle_w, top - header_block_h, status_w, header_block_h,
          "<b>Status:</b><br/><b>ND</b> – No Defect<br/><b>SDR</b> – See Defect Report<br/><b>NF</b> – Not Found",
          size=6, align=0)

    columns = [22, 47, 16, 18, 18, 18, 18, 18, 14, 13]
    widths = [value * mm for value in columns]
    headers = [
        "Identification<br/>Number", "Description", "WLL<br/>or<br/>SWL",
        "Date of Last<br/>Thorough<br/>Examination", "Date of this<br/>Thorough<br/>Examination",
        "Latest date<br/>of the next<br/>thorough<br/>examination", "Reason for<br/>Examination<br/>(See Below)",
        "Manufacturer", "Status", "Safe to<br/>Use<br/>Yes or No",
    ]
    header_y = top - header_block_h - 21 * mm
    cursor = table_x
    for width, label in zip(widths, headers, strict=True):
        _cell(canvas, cursor, header_y, width, 21 * mm, label, fill=HEADER, size=5.5, bold=True)
        cursor += width

    last_exam = inspection.inspection_date.replace(year=max(inspection.inspection_date.year - 1, 1900))
    result_code = "ND" if inspection.status == "approved" else "SDR"
    description = f"{equipment.name}<br/>{equipment.type.name}<br/>MFD: {equipment.manufacture_year or '—'}"
    row_values = [
        equipment.serial_number or equipment.code,
        description,
        equipment.capacity or "—",
        _fmt(last_exam),
        _fmt(inspection.inspection_date),
        _fmt(certificate.expires_at),
        certificate.reason_code,
        equipment.manufacturer or "—",
        result_code,
        "Yes" if certificate.safe_to_use else "No",
    ]
    row_h = 20 * mm
    row_y = header_y - row_h
    cursor = table_x
    for width, value in zip(widths, row_values, strict=True):
        _cell(canvas, cursor, row_y, width, row_h, value, size=5.7)
        cursor += width
    blank_y = row_y - row_h
    cursor = table_x
    for width in widths:
        _cell(canvas, cursor, blank_y, width, row_h, "")
        cursor += width

    reason_h = 12 * mm
    reason_y = blank_y - reason_h
    reason_widths = [22, 47, 34, 34, 34, table_w / mm - 171]
    reason_labels = ["Reason for<br/>Examination", "Installation:  <b>A</b>", "6 Monthly:  <b>B</b>",
                     "Annual:  <b>C</b>", "Written Scheme:  <b>D</b>", "Exceptional<br/>Circumstance:  <b>E</b>"]
    cursor = table_x
    for index, (width_mm, label) in enumerate(zip(reason_widths, reason_labels, strict=True)):
        _cell(canvas, cursor, reason_y, width_mm * mm, reason_h, label, size=5.8, bold=index == 0, align=0)
        cursor += width_mm * mm

    signature_h = 32 * mm
    signature_y = reason_y - signature_h
    signature_left_w = 122 * mm
    _cell(canvas, table_x, signature_y, signature_left_w, signature_h, "")
    _cell(canvas, table_x + signature_left_w, signature_y, table_w - signature_left_w, signature_h, "")
    inspector_name = inspection.inspector.full_name if inspection.inspector else "FNLIFTING Technical Team"
    inspector_qualifications = inspector_profile.qualifications if inspector_profile else "Authorized lifting equipment inspector"
    _paragraph(canvas,
               f"Name & qualifications of the person making this report:<br/><b>{inspector_name}</b><br/>{inspector_qualifications}",
               table_x + 1.5 * mm, signature_y + 11 * mm, 72 * mm, 19 * mm, size=5.7, align=0)
    canvas.setFont("Helvetica", 6.2)
    canvas.drawString(table_x + 1.5 * mm, signature_y + 2.3 * mm,
                      f"Signature: {inspector_profile.inspector_code if inspector_profile else '—'}")
    _draw_signatory_asset(canvas, inspector_profile, table_x + 29 * mm, signature_y + 1.5 * mm, 65 * mm, 20 * mm)

    approver_name = approver.employee.full_name if approver else "Authorized Technical Supervisor"
    _paragraph(canvas, "Name of the person signing or authenticating this report on behalf of the author:",
               table_x + signature_left_w + 1.5 * mm, signature_y + 22 * mm, table_w - signature_left_w - 3 * mm,
               8 * mm, size=5.2, align=0)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawString(table_x + signature_left_w + 1.5 * mm, signature_y + 10 * mm, approver_name)
    _draw_signatory_asset(canvas, approver, table_x + signature_left_w + 20 * mm, signature_y + 1.5 * mm, 50 * mm, 22 * mm)

    footer_y = 8 * mm
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 5.7)
    canvas.drawCentredString(page_width / 2, footer_y + 10 * mm, "FNLIFTING ANGOLA")
    canvas.setFont("Helvetica", 5.2)
    canvas.drawCentredString(page_width / 2, footer_y + 7 * mm,
                             "Centralidade do Sequele, Bloco 1, Rua 2, Edificio 18A, Apto 002")
    canvas.drawCentredString(page_width / 2, footer_y + 4 * mm,
                             "Lifting Department Contact: +244 946 990 061 / 946 990 090")
    canvas.setFillColor(BRAND_BLUE)
    canvas.drawCentredString(page_width / 2, footer_y + 1 * mm, "inspections@fnlifting.com  |  www.fnlifting.com")
    verification_url = f"http://localhost:8000/api/v1/public/certificates/{certificate.qr_token}"
    _draw_qr(canvas, verification_url, page_width - 20 * mm, footer_y, 13 * mm)
    canvas.setFont("Helvetica", 4.2)
    canvas.drawCentredString(page_width - 13.5 * mm, footer_y - 1 * mm, "VERIFY")

    canvas.save()
    return output
