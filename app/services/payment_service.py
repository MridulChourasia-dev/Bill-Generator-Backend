from typing import List, Optional
from uuid import UUID
from math import ceil

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.payment import Payment
from app.models.bill import Bill, BillStatus
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentListResponse


class PaymentService:
    """Service layer for payment recording and retrieval."""

    def record_payment(
        self, db: Session, user_id: UUID, data: PaymentCreate
    ) -> Payment:
        """Record a new payment and update the related bill's status."""
        # Verify the bill exists and belongs to the user
        bill = db.query(Bill).filter(
            and_(Bill.id == data.bill_id, Bill.user_id == user_id)
        ).first()
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found",
            )

        payment = Payment(
            bill_id=data.bill_id,
            user_id=user_id,
            amount=data.amount,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
            notes=data.notes,
            payment_date=data.payment_date,
        )
        db.add(payment)

        # Auto-update bill status to PAID
        bill.status = BillStatus.PAID
        bill.paid_date = data.payment_date

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
    ) -> PaymentListResponse:
        """Get paginated payments for a user, optionally filtered by bill."""
        query = db.query(Payment).filter(Payment.user_id == user_id)
        if bill_id:
            query = query.filter(Payment.bill_id == bill_id)

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


payment_service = PaymentService()
