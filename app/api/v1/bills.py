from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.bill import BillStatus
from app.schemas.bill import (
    BillCreate, BillUpdate, BillResponse, BillListResponse,
    MarkAsPaidRequest, BillCloneRequest, BulkBillActionRequest,
    BillStatsResponse, BillSortField,
)
from app.services.bill_service import bill_service
from app.middleware.auth_middleware import get_current_user
from app.services.pdf_service import pdf_service
from app.services.excel_service import excel_service

router = APIRouter()


# ─── Static routes MUST come before /{bill_id} ──────────────────────────


# ─── GET /stats ──────────────────────────────────────────────────────────
@router.get("/stats", response_model=BillStatsResponse)
def get_bill_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bill statistics summary (counts, totals by status)."""
    return bill_service.get_bill_stats(db, current_user.id)


# ─── GET /categories ─────────────────────────────────────────────────────
@router.get("/categories", response_model=List[str])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all unique bill categories used by the current user."""
    return bill_service.get_user_categories(db, current_user.id)


# ─── GET /overdue/list ───────────────────────────────────────────────────
@router.get("/overdue/list", response_model=List[BillResponse])
def get_overdue_bills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all overdue bills for the current user."""
    return bill_service.get_overdue_bills(db, current_user.id)


# ─── GET /upcoming ───────────────────────────────────────────────────────
@router.get("/upcoming", response_model=List[BillResponse])
def get_upcoming_bills(
    days: int = Query(7, ge=1, le=90, description="Number of days ahead to look"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bills due within the next N days."""
    return bill_service.get_upcoming_bills(db, current_user.id, days=days)


# ─── GET /export-excel ────────────────────────────────────────────────────
@router.get("/export-excel")
def export_bills_excel(
    status_filter: Optional[BillStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all of the current user's bills to an Excel file."""
    bills = bill_service.get_all_user_bills(db, current_user.id, status_filter=status_filter)

    bill_list = []
    for b in bills:
        bill_list.append({
            "Title": b.title,
            "Amount": float(b.amount),
            "Vendor": b.vendor or "N/A",
            "Category": b.category or "N/A",
            "Status": b.status.value if hasattr(b.status, "value") else str(b.status),
            "Frequency": b.frequency.value if hasattr(b.frequency, "value") else str(b.frequency),
            "Bill Date": b.bill_date.strftime("%Y-%m-%d"),
            "Due Date": b.due_date.strftime("%Y-%m-%d"),
            "Paid Date": b.paid_date.strftime("%Y-%m-%d") if b.paid_date else "N/A",
            "Description": b.description or "",
            "Notes": b.notes or "",
        })

    file_path = excel_service.generate_bill_export(bill_list)

    return FileResponse(
        path=file_path,
        filename=f"bills_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ─── POST /bulk-action ──────────────────────────────────────────────────
@router.post("/bulk-action")
def bulk_bill_action(
    data: BulkBillActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perform a bulk action on multiple bills (delete, cancel, mark-paid)."""
    result = bill_service.bulk_action(db, current_user.id, data)
    return result


# ─── POST / ──────────────────────────────────────────────────────────────
@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    data: BillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new bill."""
    return bill_service.create_bill(db, current_user.id, data)


# ─── GET / ───────────────────────────────────────────────────────────────
@router.get("/", response_model=BillListResponse)
def get_bills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[BillStatus] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[BillSortField] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
    date_from: Optional[datetime] = Query(None, description="Filter bills from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter bills up to this date"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum bill amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum bill amount"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a paginated list of the current user's bills with advanced filtering."""
    return bill_service.get_bills(
        db, current_user.id,
        page=page, per_page=per_page,
        status=status, category=category, search=search,
        sort_by=sort_by, sort_order=sort_order,
        date_from=date_from, date_to=date_to,
        min_amount=min_amount, max_amount=max_amount,
    )


# ─── GET /{bill_id} ───────────────────────────────────────────────────────
@router.get("/{bill_id}", response_model=BillResponse)
def get_bill(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific bill by ID."""
    return bill_service.get_bill_by_id(db, bill_id, current_user.id)


# ─── PUT /{bill_id} ───────────────────────────────────────────────────────
@router.put("/{bill_id}", response_model=BillResponse)
def update_bill(
    bill_id: UUID,
    data: BillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a bill's details."""
    return bill_service.update_bill(db, bill_id, current_user.id, data)


# ─── DELETE /{bill_id} ────────────────────────────────────────────────────
@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a bill."""
    bill_service.delete_bill(db, bill_id, current_user.id)


# ─── POST /{bill_id}/mark-paid ───────────────────────────────────────────
@router.post("/{bill_id}/mark-paid", response_model=BillResponse)
def mark_bill_paid(
    bill_id: UUID,
    data: MarkAsPaidRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a bill as paid."""
    return bill_service.mark_as_paid(db, bill_id, current_user.id, data.paid_date)


# ─── POST /{bill_id}/clone ──────────────────────────────────────────────
@router.post("/{bill_id}/clone", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
def clone_bill(
    bill_id: UUID,
    data: BillCloneRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clone/duplicate an existing bill with optional overrides."""
    return bill_service.clone_bill(db, bill_id, current_user.id, data)


# ─── GET /{bill_id}/download-pdf ──────────────────────────────────────────
@router.get("/{bill_id}/download-pdf")
def download_bill_pdf(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a specific bill's receipt as a PDF."""
    bill = bill_service.get_bill_by_id(db, bill_id, current_user.id)

    file_path = pdf_service.generate_bill_receipt(
        bill_id=str(bill.id),
        bill_title=bill.title,
        vendor=bill.vendor,
        amount=float(bill.amount),
        status=bill.status.value if hasattr(bill.status, "value") else str(bill.status),
        bill_date=bill.bill_date.strftime("%Y-%m-%d"),
        due_date=bill.due_date.strftime("%Y-%m-%d"),
        paid_date=bill.paid_date.strftime("%Y-%m-%d") if bill.paid_date else None,
        user_name=current_user.full_name or current_user.username,
        user_email=current_user.email,
    )

    return FileResponse(
        path=file_path,
        filename=f"bill_{bill_id}.pdf",
        media_type="application/pdf",
    )
