from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table, TableStyle

from app.core.config import BACKEND_DIR, INVOICE_DIR, RECEIPT_DIR
from app.models import Invoice, Receipt


INVOICE_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
LOGO = BACKEND_DIR / "app" / "pdf" / "assets" / "fnlifting-certificate-logo.png"
NAVY = colors.HexColor("#08274A")
BLUE = colors.HexColor("#087EFF")


def _money(value) -> str:
    return f"Kz {float(value):,.2f}".replace(",", " ")


def _header(canvas: Canvas, title: str, number: str) -> None:
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 43 * mm, width, 43 * mm, fill=1, stroke=0)
    if LOGO.exists():
        canvas.drawImage(str(LOGO), 13 * mm, height - 36 * mm, 43 * mm, 26 * mm, preserveAspectRatio=True, mask="auto")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 19)
    canvas.drawRightString(width - 15 * mm, height - 22 * mm, title)
    canvas.setFillColor(colors.HexColor("#8DC8FF"))
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawRightString(width - 15 * mm, height - 30 * mm, number)


def generate_invoice_pdf(invoice: Invoice) -> Path:
    output = INVOICE_DIR / f"{invoice.invoice_no}.pdf"
    canvas = Canvas(str(output), pagesize=A4, pageCompression=1)
    width, height = A4
    _header(canvas, "FATURA", invoice.invoice_no)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(15 * mm, height - 58 * mm, "FATURADO A")
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(15 * mm, height - 66 * mm, invoice.client.name)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(15 * mm, height - 72 * mm, f"NIF: {invoice.client.nif}")
    canvas.drawString(15 * mm, height - 78 * mm, invoice.client.address or "Angola")
    canvas.drawRightString(width - 15 * mm, height - 60 * mm, f"Emissão: {invoice.issue_date:%d/%m/%Y}")
    canvas.drawRightString(width - 15 * mm, height - 67 * mm, f"Vencimento: {invoice.due_date:%d/%m/%Y}")
    data = [["DESCRIÇÃO", "QTD.", "PREÇO UNIT.", "IVA", "TOTAL"]]
    for item in invoice.items:
        data.append([item.description, str(item.quantity), _money(item.unit_price), f"{item.tax_rate}%", _money(item.line_total)])
    table = Table(data, colWidths=[86 * mm, 18 * mm, 31 * mm, 18 * mm, 31 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#B7C8D8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F7FC")]),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    table.wrapOn(canvas, width, height)
    table.drawOn(canvas, 13 * mm, height - 93 * mm - table._height)
    y = height - 102 * mm - table._height
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(width - 15 * mm, y, f"Subtotal: {_money(invoice.subtotal)}")
    canvas.drawRightString(width - 15 * mm, y - 7 * mm, f"IVA: {_money(invoice.tax_amount)}")
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawRightString(width - 15 * mm, y - 16 * mm, f"Total: {_money(invoice.total_amount)}")
    canvas.setFillColor(colors.HexColor("#60758B"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(15 * mm, 24 * mm, invoice.notes or "Obrigado pela sua preferência.")
    canvas.drawCentredString(width / 2, 12 * mm, "FNLIFTING ANGOLA · Centralidade do Sequele · Luanda · Angola")
    canvas.save()
    return output


def generate_receipt_pdf(receipt: Receipt) -> Path:
    output = RECEIPT_DIR / f"{receipt.receipt_no}.pdf"
    canvas = Canvas(str(output), pagesize=A4, pageCompression=1)
    width, height = A4
    _header(canvas, "RECIBO", receipt.receipt_no)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(18 * mm, height - 62 * mm, f"Recebemos de: {receipt.client.name}")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(18 * mm, height - 72 * mm, f"NIF: {receipt.client.nif}")
    canvas.drawString(18 * mm, height - 82 * mm, f"Referente à fatura: {receipt.invoice.invoice_no}")
    canvas.drawString(18 * mm, height - 92 * mm, f"Forma de pagamento: {receipt.payment.method}")
    canvas.drawString(18 * mm, height - 102 * mm, f"Data: {receipt.issued_at:%d/%m/%Y}")
    canvas.setFillColor(colors.HexColor("#EAF4FF"))
    canvas.roundRect(18 * mm, height - 135 * mm, width - 36 * mm, 21 * mm, 4 * mm, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(width / 2, height - 127 * mm, _money(receipt.amount))
    canvas.setFillColor(colors.HexColor("#60758B"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(width / 2, 12 * mm, "Documento emitido eletronicamente pelo FNLIFTING Enterprise ERP")
    canvas.save()
    return output
