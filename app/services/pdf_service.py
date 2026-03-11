from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.config import settings

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating professional PDF receipts and reports."""

    def __init__(self):
        self.output_dir = Path(settings.PDF_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="DocTitle", fontSize=22, textColor=colors.HexColor("#2c3e50"),
            spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"
        ))
        styles.add(ParagraphStyle(
            name="DocSubTitle", fontSize=12, textColor=colors.HexColor("#7f8c8d"),
            spaceAfter=4, alignment=TA_CENTER
        ))
        styles.add(ParagraphStyle(
            name="SectionHeader", fontSize=12, textColor=colors.HexColor("#2980b9"),
            spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold"
        ))
        styles.add(ParagraphStyle(
            name="Normal2", fontSize=10, textColor=colors.HexColor("#2c3e50"), spaceAfter=4
        ))
        styles.add(ParagraphStyle(
            name="Right", fontSize=10, textColor=colors.HexColor("#2c3e50"),
            spaceAfter=4, alignment=TA_RIGHT
        ))
        return styles

    def generate_bill_receipt(
        self,
        bill_id: str,
        bill_title: str,
        vendor: Optional[str],
        amount: float,
        status: str,
        bill_date: str,
        due_date: str,
        paid_date: Optional[str],
        user_name: str,
        user_email: str,
        payment_method: Optional[str] = None,
        reference_number: Optional[str] = None,
    ) -> Path:
        """Generate a professional bill/payment receipt PDF."""
        file_name = f"receipt_{bill_id}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = self.output_dir / file_name

        doc = SimpleDocTemplate(
            str(file_path), pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm
        )
        styles = self._get_styles()
        story = []

        # Header
        story.append(Paragraph("BILL GENERATOR", styles["DocTitle"]))
        story.append(Paragraph("Payment Receipt", styles["DocSubTitle"]))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2980b9")))
        story.append(Spacer(1, 0.4 * cm))

        # Receipt metadata
        receipt_no = f"REC-{uuid.uuid4().hex[:8].upper()}"
        generated_at = datetime.now().strftime("%d %B %Y, %I:%M %p")
        meta_data = [
            ["Receipt No:", receipt_no, "Date:", generated_at],
        ]
        meta_table = Table(meta_data, colWidths=[4 * cm, 7 * cm, 3 * cm, 5 * cm])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#7f8c8d")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#7f8c8d")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4 * cm))

        # Customer info
        story.append(Paragraph("Bill To:", styles["SectionHeader"]))
        story.append(Paragraph(f"<b>{user_name}</b>", styles["Normal2"]))
        story.append(Paragraph(user_email, styles["Normal2"]))
        story.append(Spacer(1, 0.4 * cm))

        # Bill details table
        story.append(Paragraph("Bill Details:", styles["SectionHeader"]))
        detail_data = [
            ["Field", "Details"],
            ["Bill Title", bill_title],
            ["Vendor", vendor or "N/A"],
            ["Bill Date", bill_date],
            ["Due Date", due_date],
            ["Paid Date", paid_date or "Not Paid"],
            ["Status", status.upper()],
            ["Payment Method", payment_method or "N/A"],
            ["Reference No.", reference_number or "N/A"],
        ]
        detail_table = Table(detail_data, colWidths=[6 * cm, 11 * cm])
        detail_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 0.6 * cm))

        # Amount box
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dee2e6")))
        amount_data = [["Total Amount", f"${amount:,.2f}"]]
        amount_table = Table(amount_data, colWidths=[14 * cm, 3 * cm])
        amount_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 14),
            ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#27ae60")),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(amount_table)
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dee2e6")))

        # Footer
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(
            "Thank you for using Bill Generator! This is a system-generated receipt.",
            styles["DocSubTitle"]
        ))

        doc.build(story)
        logger.info(f"Generated PDF receipt: {file_path}")
        return file_path

    def generate_payment_receipt(
        self,
        payment_id: str,
        bill_title: str,
        amount: float,
        payment_method: str,
        payment_date: str,
        reference_number: Optional[str],
        user_name: str,
        user_email: str,
    ) -> Path:
        """Generate a standalone payment receipt PDF."""
        file_name = f"payment_{payment_id}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = self.output_dir / file_name

        doc = SimpleDocTemplate(str(file_path), pagesize=A4,
                                rightMargin=2 * cm, leftMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm)
        styles = self._get_styles()
        story = []

        story.append(Paragraph("PAYMENT RECEIPT", styles["DocTitle"]))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#27ae60")))
        story.append(Spacer(1, 0.5 * cm))

        data = [
            ["Bill", bill_title],
            ["Amount Paid", f"${amount:,.2f}"],
            ["Payment Method", payment_method.replace("_", " ").title()],
            ["Payment Date", payment_date],
            ["Reference No.", reference_number or "N/A"],
            ["Recipient", user_name],
            ["Email", user_email],
        ]
        table = Table(data, colWidths=[6 * cm, 11 * cm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(table)
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph("✓ Payment successfully recorded.", styles["DocSubTitle"]))

        doc.build(story)
        logger.info(f"Generated payment PDF: {file_path}")
        return file_path

    def generate_report(
        self,
        user_name: str,
        report_period: str,
        total_bills: int,
        paid_bills: int,
        overdue_bills: int,
        total_amount_due: float,
        total_amount_paid: float,
    ) -> Path:
        """Generate a monthly/periodic summary report PDF."""
        file_name = f"report_{uuid.uuid4().hex[:8]}.pdf"
        file_path = self.output_dir / file_name

        doc = SimpleDocTemplate(str(file_path), pagesize=A4,
                                rightMargin=2 * cm, leftMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm)
        styles = self._get_styles()
        story = []

        story.append(Paragraph("BILL GENERATOR", styles["DocTitle"]))
        story.append(Paragraph(f"Summary Report — {report_period}", styles["DocSubTitle"]))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#8e44ad")))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(f"Prepared for: <b>{user_name}</b>", styles["Normal2"]))
        story.append(Spacer(1, 0.5 * cm))

        summary_data = [
            ["Metric", "Value"],
            ["Total Bills", str(total_bills)],
            ["Paid Bills", str(paid_bills)],
            ["Overdue Bills", str(overdue_bills)],
            ["Pending Bills", str(total_bills - paid_bills - overdue_bills)],
            ["Total Amount Due", f"${total_amount_due:,.2f}"],
            ["Total Amount Paid", f"${total_amount_paid:,.2f}"],
            ["Outstanding", f"${total_amount_due - total_amount_paid:,.2f}"],
        ]
        table = Table(summary_data, colWidths=[9 * cm, 8 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(table)

        doc.build(story)
        logger.info(f"Generated report PDF: {file_path}")
        return file_path


pdf_service = PDFService()
