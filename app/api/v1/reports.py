from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import csv
import io
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.models.user import User
from app.services.report_service import report_service
from app.services.pdf_service import pdf_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics for the current user."""
    return report_service.get_dashboard_stats(db, current_user.id)


@router.get("/bills")
def get_bill_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bill breakdown report by status and category."""
    return report_service.get_bill_report(db, current_user.id)


@router.get("/payments")
def get_payment_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment report by method and monthly summary."""
    return report_service.get_payment_report(db, current_user.id)


@router.get("/analytics")
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive analytics data for charts and dashboards."""
    return report_service.get_analytics(db, current_user.id)


@router.get("/export")
def export_report(
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a summary report in PDF or CSV format."""
    from datetime import datetime
    stats = report_service.get_dashboard_stats(db, current_user.id)

    if format == "pdf":
        pdf_path = pdf_service.generate_report(
            user_name=current_user.full_name or current_user.username,
            report_period=datetime.now().strftime("%B %Y"),
            total_bills=stats["total_bills"],
            paid_bills=stats["paid_bills"],
            overdue_bills=stats["overdue_bills"],
            total_amount_due=stats["total_amount_due"],
            total_amount_paid=stats["total_amount_paid"],
        )
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=f"report_{datetime.now().strftime('%Y%m')}.pdf",
        )

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Bills", stats["total_bills"]])
    writer.writerow(["Paid Bills", stats["paid_bills"]])
    writer.writerow(["Overdue Bills", stats["overdue_bills"]])
    writer.writerow(["Pending Bills", stats["pending_bills"]])
    writer.writerow(["Total Amount Due", f"${stats['total_amount_due']:,.2f}"])
    writer.writerow(["Total Amount Paid", f"${stats['total_amount_paid']:,.2f}"])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{datetime.now().strftime('%Y%m')}.csv"},
    )
