from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from datetime import date


def generate_certificate_pdf(student_name: str, course_name: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setStrokeColor(HexColor("#2c3e50"))
    c.setLineWidth(3)
    c.rect(1.5 * cm, 1.5 * cm, width - 3 * cm, height - 3 * cm)

    c.setFont("Helvetica-Bold", 32)
    c.setFillColor(HexColor("#2c3e50"))
    c.drawCentredString(width / 2, height - 4 * cm, "SERTIFIKAT PENYELESAIAN")

    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 5.5 * cm, "Diberikan kepada:")

    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(HexColor("#000000"))
    c.drawCentredString(width / 2, height - 7 * cm, student_name)

    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(
        width / 2,
        height - 9 * cm,
        f"Atas partisipasi dan penyelesaian matkul \"{course_name}\""
    )

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        width / 2,
        3 * cm,
        f"Diterbitkan pada {date.today().strftime('%d %B %Y')}"
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()