from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse, PaymentListResponse
from app.services.payment_service import payment_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


# ─── POST / ──────────────────────────────────────────────────────────────
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a new payment for a bill."""
    return payment_service.record_payment(db, current_user.id, data)


# ─── GET / ───────────────────────────────────────────────────────────────
@router.get("/", response_model=PaymentListResponse)
def get_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    bill_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated payments, optionally filtered by bill."""
    return payment_service.get_payments(
        db, current_user.id, bill_id=bill_id, page=page, per_page=per_page
    )


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
    """Delete a payment record."""
    payment_service.delete_payment(db, payment_id, current_user.id)


# ─── GET /bill/{bill_id} ─────────────────────────────────────────────────
@router.get("/bill/{bill_id}", response_model=List[PaymentResponse])
def get_bill_payments(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all payments for a specific bill."""
    return payment_service.get_bill_payments(db, bill_id, current_user.id)
