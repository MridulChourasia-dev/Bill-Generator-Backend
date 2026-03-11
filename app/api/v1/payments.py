from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.payment import PaymentMethod
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse, PaymentListResponse
from app.services.payment_service import payment_service
from app.services.pdf_service import pdf_service
from app.services.excel_service import excel_service
from app.services.email_service import email_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


# ─── Static routes MUST come before /{payment_id} ────────────────────────


# ─── GET /export-excel ───────────────────────────────────────────────────
@router.get("/export-excel")
def export_payments_excel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all payments to an Excel file."""
    payments = payment_service.get_all_user_payments(db, current_user.id)

    payment_list = []
    for p in payments:
        payment_list.append({
            "Bill ID": str(p.bill_id),
            "Amount": float(p.amount),
            "Payment Method": p.payment_method.value if hasattr(p.payment_method, "value") else str(p.payment_method),
            "Status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "Reference Number": p.reference_number or "N/A",
            "Payment Date": p.payment_date.strftime("%Y-%m-%d"),
            "Notes": p.notes or "",
        })

    file_path = excel_service.generate_bill_export(payment_list, filename_prefix="payments_export")

    return FileResponse(
        path=file_path,
        filename=f"payments_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ─── POST / ──────────────────────────────────────────────────────────────
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    data: PaymentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a new payment for a bill. Sends email confirmation in background."""
    payment = payment_service.record_payment(db, current_user.id, data)

    # Send payment confirmation email in background
    bill = payment.bill
    if current_user.email_notifications and bill:
        background_tasks.add_task(
            email_service.send_payment_confirmation,
            to_email=current_user.email,
            user_name=current_user.full_name or current_user.username,
            bill_title=bill.title,
            amount=float(payment.amount),
            payment_date=payment.payment_date.strftime("%d %b %Y"),
        )

    return payment


# ─── GET / ───────────────────────────────────────────────────────────────
@router.get("/", response_model=PaymentListResponse)
def get_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    bill_id: Optional[UUID] = None,
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    payment_method: Optional[PaymentMethod] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated payments with optional date and method filters."""
    return payment_service.get_payments(
        db, current_user.id,
        bill_id=bill_id, page=page, per_page=per_page,
        date_from=date_from, date_to=date_to,
        payment_method=payment_method,
    )


# ─── GET /bill/{bill_id} ─────────────────────────────────────────────────
@router.get("/bill/{bill_id}", response_model=List[PaymentResponse])
def get_bill_payments(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all payments for a specific bill."""
    return payment_service.get_bill_payments(db, bill_id, current_user.id)


# ─── GET /bill/{bill_id}/summary ──────────────────────────────────────────
@router.get("/bill/{bill_id}/summary")
def get_bill_payment_summary(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment summary for a bill (total paid, remaining balance, etc.)."""
    return payment_service.get_bill_payment_summary(db, bill_id, current_user.id)


# ─── GET /{payment_id} ───────────────────────────────────────────────────
@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific payment by ID."""
    return payment_service.get_payment_by_id(db, payment_id, current_user.id)


# ─── PUT /{payment_id} ───────────────────────────────────────────────────
@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: UUID,
    data: PaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a payment record."""
    return payment_service.update_payment(db, payment_id, current_user.id, data)


# ─── DELETE /{payment_id} ────────────────────────────────────────────────
@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a payment record. Reverts bill status if needed."""
    payment_service.delete_payment(db, payment_id, current_user.id)


# ─── GET /{payment_id}/download-receipt ───────────────────────────────────
@router.get("/{payment_id}/download-receipt")
def download_payment_receipt(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a payment receipt as a PDF."""
    payment = payment_service.get_payment_by_id(db, payment_id, current_user.id)
    bill = payment.bill

    file_path = pdf_service.generate_payment_receipt(
        payment_id=str(payment.id),
        bill_title=bill.title if bill else "N/A",
        amount=float(payment.amount),
        payment_method=payment.payment_method.value if hasattr(payment.payment_method, "value") else str(payment.payment_method),
        payment_date=payment.payment_date.strftime("%Y-%m-%d"),
        reference_number=payment.reference_number,
        user_name=current_user.full_name or current_user.username,
        user_email=current_user.email,
    )

    return FileResponse(
        path=file_path,
        filename=f"receipt_{payment_id}.pdf",
        media_type="application/pdf",
    )
