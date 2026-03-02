from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.bill import BillStatus
from app.schemas.bill import BillCreate, BillUpdate, BillResponse, BillListResponse, MarkAsPaidRequest
from app.services.bill_service import bill_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a paginated list of the current user's bills."""
    return bill_service.get_bills(
        db, current_user.id, page=page, per_page=per_page,
        status=status, category=category, search=search,
    )


# ─── GET /overdue/list ───────────────────────────────────────────────────
@router.get("/overdue/list", response_model=List[BillResponse])
def get_overdue_bills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all overdue bills for the current user."""
    return bill_service.get_overdue_bills(db, current_user.id)


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
