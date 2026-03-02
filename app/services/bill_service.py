from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from math import ceil

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from app.models.bill import Bill, BillStatus
from app.schemas.bill import BillCreate, BillUpdate, BillListResponse


class BillService:
    """Service layer for all bill-related operations."""

    def create_bill(self, db: Session, user_id: UUID, data: BillCreate) -> Bill:
        """Create a new bill for the authenticated user."""
        bill = Bill(
            user_id=user_id,
            title=data.title,
            description=data.description,
            amount=data.amount,
            frequency=data.frequency,
            vendor=data.vendor,
            category=data.category,
            notes=data.notes,
            bill_date=data.bill_date,
            due_date=data.due_date,
            status=BillStatus.PENDING,
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)
        return bill

    def get_bills(
        self,
        db: Session,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: Optional[BillStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> BillListResponse:
        """Get paginated bills for a user with optional filtering."""
        query = db.query(Bill).filter(Bill.user_id == user_id)

        if status:
            query = query.filter(Bill.status == status)
        if category:
            query = query.filter(Bill.category == category)
        if search:
            query = query.filter(
                or_(
                    Bill.title.ilike(f"%{search}%"),
                    Bill.vendor.ilike(f"%{search}%"),
                    Bill.description.ilike(f"%{search}%"),
                )
            )

        total = query.count()
        bills = (
            query.order_by(Bill.due_date.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return BillListResponse(
            bills=bills,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=ceil(total / per_page) if total else 0,
        )

    def get_bill_by_id(self, db: Session, bill_id: UUID, user_id: UUID) -> Bill:
        """Fetch a single bill, ensuring it belongs to the requesting user."""
        bill = db.query(Bill).filter(
            and_(Bill.id == bill_id, Bill.user_id == user_id)
        ).first()
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found",
            )
        return bill

    def update_bill(
        self, db: Session, bill_id: UUID, user_id: UUID, data: BillUpdate
    ) -> Bill:
        """Update specified fields of an existing bill."""
        bill = self.get_bill_by_id(db, bill_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(bill, field, value)
        db.commit()
        db.refresh(bill)
        return bill

    def delete_bill(self, db: Session, bill_id: UUID, user_id: UUID) -> None:
        """Permanently delete a bill."""
        bill = self.get_bill_by_id(db, bill_id, user_id)
        db.delete(bill)
        db.commit()

    def mark_as_paid(
        self,
        db: Session,
        bill_id: UUID,
        user_id: UUID,
        paid_date: Optional[datetime] = None,
    ) -> Bill:
        """Mark a bill as paid and record the payment date."""
        bill = self.get_bill_by_id(db, bill_id, user_id)
        if bill.status == BillStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bill is already marked as paid",
            )
        bill.status = BillStatus.PAID
        bill.paid_date = paid_date or datetime.now(timezone.utc)
        db.commit()
        db.refresh(bill)
        return bill

    def get_overdue_bills(self, db: Session, user_id: UUID) -> List[Bill]:
        """Return all overdue bills for a user."""
        now = datetime.now(timezone.utc)
        return (
            db.query(Bill)
            .filter(
                and_(
                    Bill.user_id == user_id,
                    Bill.due_date < now,
                    Bill.status == BillStatus.PENDING,
                )
            )
            .order_by(Bill.due_date.asc())
            .all()
        )

    def mark_overdue_bills(self, db: Session) -> int:
        """Background job: mark all pending past-due bills as OVERDUE."""
        now = datetime.now(timezone.utc)
        updated = (
            db.query(Bill)
            .filter(
                and_(Bill.due_date < now, Bill.status == BillStatus.PENDING)
            )
            .update({"status": BillStatus.OVERDUE}, synchronize_session=False)
        )
        db.commit()
        return updated


bill_service = BillService()
