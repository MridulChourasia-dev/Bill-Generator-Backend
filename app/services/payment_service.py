from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from math import ceil
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status

from app.models.payment import Payment, PaymentStatus
from app.models.bill import Bill, BillStatus
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentListResponse


class PaymentService:
    """Service layer for payment recording and retrieval."""

    def record_payment(
        self, db: Session, user_id: UUID, data: PaymentCreate
    ) -> Payment:
        """Record a new payment and intelligently update the related bill's status."""
        # Verify the bill exists and belongs to the user
        bill = db.query(Bill).filter(
            and_(Bill.id == data.bill_id, Bill.user_id == user_id)
        ).first()
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found",
            )

        if bill.status in (BillStatus.CANCELLED, BillStatus.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record payment for a {bill.status.value} bill",
            )

        # Validate payment amount doesn't exceed remaining balance
        total_paid = (
            db.query(func.sum(Payment.amount))
            .filter(
                and_(
                    Payment.bill_id == data.bill_id,
                    Payment.status == PaymentStatus.COMPLETED,
                )
            )
            .scalar()
            or Decimal("0.00")
        )

        remaining = bill.amount - total_paid
        if data.amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({data.amount}) exceeds remaining balance ({remaining})",
            )

        payment = Payment(
            bill_id=data.bill_id,
            user_id=user_id,
            amount=data.amount,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
            notes=data.notes,
            payment_date=data.payment_date,
            status=PaymentStatus.COMPLETED,
        )
        db.add(payment)

        # Auto-update bill status based on total paid
        new_total_paid = total_paid + data.amount
        if new_total_paid >= bill.amount:
            bill.status = BillStatus.PAID
            bill.paid_date = data.payment_date
        # (partial payment keeps bill in its current status)

        db.commit()
        db.refresh(payment)
        return payment

    def get_payments(
        self,
        db: Session,
        user_id: UUID,
        bill_id: Optional[UUID] = None,
        page: int = 1,
        per_page: int = 20,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        payment_method: Optional[str] = None,
    ) -> PaymentListResponse:
        """Get paginated payments for a user with optional filters."""
        query = db.query(Payment).filter(Payment.user_id == user_id)

        if bill_id:
            query = query.filter(Payment.bill_id == bill_id)
        if date_from:
            query = query.filter(Payment.payment_date >= date_from)
        if date_to:
            query = query.filter(Payment.payment_date <= date_to)
        if payment_method:
            query = query.filter(Payment.payment_method == payment_method)

        total = query.count()
        payments = (
            query.order_by(Payment.payment_date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return PaymentListResponse(
            payments=payments,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=ceil(total / per_page) if total else 0,
        )

    def get_payment_by_id(
        self, db: Session, payment_id: UUID, user_id: UUID
    ) -> Payment:
        payment = db.query(Payment).filter(
            and_(Payment.id == payment_id, Payment.user_id == user_id)
        ).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )
        return payment

    def update_payment(
        self, db: Session, payment_id: UUID, user_id: UUID, data: PaymentUpdate
    ) -> Payment:
        payment = self.get_payment_by_id(db, payment_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(payment, field, value)
        db.commit()
        db.refresh(payment)
        return payment

    def delete_payment(
        self, db: Session, payment_id: UUID, user_id: UUID
    ) -> None:
        payment = self.get_payment_by_id(db, payment_id, user_id)

        # When deleting a completed payment, re-check if the bill should
        # revert from PAID status back to PENDING
        if payment.status == PaymentStatus.COMPLETED:
            bill = db.query(Bill).filter(Bill.id == payment.bill_id).first()
            if bill and bill.status == BillStatus.PAID:
                total_paid = (
                    db.query(func.sum(Payment.amount))
                    .filter(
                        and_(
                            Payment.bill_id == payment.bill_id,
                            Payment.status == PaymentStatus.COMPLETED,
                            Payment.id != payment.id,  # exclude the one being deleted
                        )
                    )
                    .scalar()
                    or Decimal("0.00")
                )
                if total_paid < bill.amount:
                    bill.status = BillStatus.PENDING
                    bill.paid_date = None

        db.delete(payment)
        db.commit()

    def get_bill_payments(
        self, db: Session, bill_id: UUID, user_id: UUID
    ) -> List[Payment]:
        """Return all payments for a specific bill."""
        return (
            db.query(Payment)
            .filter(
                and_(Payment.bill_id == bill_id, Payment.user_id == user_id)
            )
            .order_by(Payment.payment_date.desc())
            .all()
        )

    def get_bill_payment_summary(
        self, db: Session, bill_id: UUID, user_id: UUID
    ) -> dict:
        """Get payment summary for a bill (total paid, remaining, etc.)."""
        bill = db.query(Bill).filter(
            and_(Bill.id == bill_id, Bill.user_id == user_id)
        ).first()
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
            )

        total_paid = (
            db.query(func.sum(Payment.amount))
            .filter(
                and_(
                    Payment.bill_id == bill_id,
                    Payment.status == PaymentStatus.COMPLETED,
                )
            )
            .scalar()
            or Decimal("0.00")
        )
        payment_count = (
            db.query(func.count(Payment.id))
            .filter(Payment.bill_id == bill_id)
            .scalar()
        )

        return {
            "bill_id": str(bill_id),
            "bill_amount": float(bill.amount),
            "total_paid": float(total_paid),
            "remaining": float(bill.amount - total_paid),
            "payment_count": payment_count,
            "is_fully_paid": total_paid >= bill.amount,
            "bill_status": bill.status.value,
        }

    def get_all_user_payments(
        self, db: Session, user_id: UUID
    ) -> List[Payment]:
        """Fetch all payments for a user (for exports)."""
        return (
            db.query(Payment)
            .filter(Payment.user_id == user_id)
            .order_by(Payment.payment_date.desc())
            .all()
        )


payment_service = PaymentService()
