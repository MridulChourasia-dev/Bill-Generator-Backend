from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from math import ceil
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status

from app.models.bill import Bill, BillStatus, BillFrequency
from app.schemas.bill import (
    BillCreate, BillUpdate, BillListResponse, BillCloneRequest,
    BulkBillActionRequest, BillStatsResponse, BillSortField,
)


class BillService:
    """Service layer for all bill-related operations."""

    # ─── Sort field mapping ──────────────────────────────────────────────
    SORT_FIELD_MAP = {
        BillSortField.title: Bill.title,
        BillSortField.amount: Bill.amount,
        BillSortField.due_date: Bill.due_date,
        BillSortField.bill_date: Bill.bill_date,
        BillSortField.created_at: Bill.created_at,
        BillSortField.status: Bill.status,
    }

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
        sort_by: Optional[BillSortField] = None,
        sort_order: Optional[str] = "asc",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ) -> BillListResponse:
        """Get paginated bills for a user with advanced filtering & sorting."""
        query = db.query(Bill).filter(Bill.user_id == user_id)

        # Status filter
        if status:
            query = query.filter(Bill.status == status)

        # Category filter
        if category:
            query = query.filter(Bill.category == category)

        # Text search
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Bill.title.ilike(search_term),
                    Bill.vendor.ilike(search_term),
                    Bill.description.ilike(search_term),
                    Bill.notes.ilike(search_term),
                )
            )

        # Date range filter (on due_date)
        if date_from:
            query = query.filter(Bill.due_date >= date_from)
        if date_to:
            query = query.filter(Bill.due_date <= date_to)

        # Amount range filter
        if min_amount is not None:
            query = query.filter(Bill.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Bill.amount <= max_amount)

        total = query.count()

        # Sorting
        if sort_by and sort_by in self.SORT_FIELD_MAP:
            column = self.SORT_FIELD_MAP[sort_by]
            order_col = column.desc() if sort_order == "desc" else column.asc()
        else:
            order_col = Bill.due_date.asc()

        bills = (
            query.order_by(order_col)
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

    def get_all_user_bills(
        self, db: Session, user_id: UUID, status_filter: Optional[BillStatus] = None
    ) -> List[Bill]:
        """Fetch all bills for a specific user without pagination."""
        query = db.query(Bill).filter(Bill.user_id == user_id)
        if status_filter:
            query = query.filter(Bill.status == status_filter)
        return query.order_by(Bill.due_date.desc()).all()

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
                    Bill.status.in_([BillStatus.PENDING, BillStatus.OVERDUE]),
                )
            )
            .order_by(Bill.due_date.asc())
            .all()
        )

    def get_upcoming_bills(
        self, db: Session, user_id: UUID, days: int = 7
    ) -> List[Bill]:
        """Return bills due within the next N days."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        return (
            db.query(Bill)
            .filter(
                and_(
                    Bill.user_id == user_id,
                    Bill.due_date >= now,
                    Bill.due_date <= future,
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

    def clone_bill(
        self,
        db: Session,
        bill_id: UUID,
        user_id: UUID,
        overrides: Optional[BillCloneRequest] = None,
    ) -> Bill:
        """Clone an existing bill with optional field overrides."""
        source = self.get_bill_by_id(db, bill_id, user_id)
        new_bill = Bill(
            user_id=user_id,
            title=overrides.title if (overrides and overrides.title) else f"{source.title} (Copy)",
            description=source.description,
            amount=overrides.amount if (overrides and overrides.amount) else source.amount,
            frequency=source.frequency,
            vendor=source.vendor,
            category=source.category,
            notes=overrides.notes if (overrides and overrides.notes) else source.notes,
            bill_date=overrides.bill_date if (overrides and overrides.bill_date) else datetime.now(timezone.utc),
            due_date=overrides.due_date if (overrides and overrides.due_date) else source.due_date,
            status=BillStatus.PENDING,
        )
        db.add(new_bill)
        db.commit()
        db.refresh(new_bill)
        return new_bill

    def bulk_action(
        self, db: Session, user_id: UUID, data: BulkBillActionRequest
    ) -> Dict[str, Any]:
        """Perform bulk operations on multiple bills."""
        bills = (
            db.query(Bill)
            .filter(and_(Bill.id.in_(data.bill_ids), Bill.user_id == user_id))
            .all()
        )

        if not bills:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching bills found",
            )

        processed = 0
        skipped = 0

        for bill in bills:
            if data.action == "delete":
                db.delete(bill)
                processed += 1
            elif data.action == "cancel":
                if bill.status not in (BillStatus.PAID, BillStatus.CANCELLED):
                    bill.status = BillStatus.CANCELLED
                    processed += 1
                else:
                    skipped += 1
            elif data.action == "mark_paid":
                if bill.status != BillStatus.PAID:
                    bill.status = BillStatus.PAID
                    bill.paid_date = datetime.now(timezone.utc)
                    processed += 1
                else:
                    skipped += 1

        db.commit()
        return {
            "action": data.action,
            "processed": processed,
            "skipped": skipped,
            "total_requested": len(data.bill_ids),
        }

    def get_user_categories(self, db: Session, user_id: UUID) -> List[str]:
        """Return all unique categories used by a user's bills."""
        rows = (
            db.query(Bill.category)
            .filter(and_(Bill.user_id == user_id, Bill.category.isnot(None)))
            .distinct()
            .order_by(Bill.category)
            .all()
        )
        return [row[0] for row in rows]

    def get_bill_stats(self, db: Session, user_id: UUID) -> BillStatsResponse:
        """Compute aggregated bill statistics for the user."""
        base = db.query(Bill).filter(Bill.user_id == user_id)

        total_count = base.count()

        def _count(s: BillStatus) -> int:
            return base.filter(Bill.status == s).count()

        def _amount(s: BillStatus) -> float:
            val = base.filter(Bill.status == s).with_entities(func.sum(Bill.amount)).scalar()
            return float(val or 0)

        total_amount = float(
            base.with_entities(func.sum(Bill.amount)).scalar() or 0
        )

        return BillStatsResponse(
            total_count=total_count,
            pending_count=_count(BillStatus.PENDING),
            paid_count=_count(BillStatus.PAID),
            overdue_count=_count(BillStatus.OVERDUE),
            cancelled_count=_count(BillStatus.CANCELLED),
            draft_count=_count(BillStatus.DRAFT),
            total_amount=total_amount,
            pending_amount=_amount(BillStatus.PENDING),
            paid_amount=_amount(BillStatus.PAID),
            overdue_amount=_amount(BillStatus.OVERDUE),
        )

    def generate_recurring_bills(self, db: Session) -> int:
        """Background task: auto-generate next bill for recurring bills that are paid."""
        frequency_delta = {
            BillFrequency.DAILY: timedelta(days=1),
            BillFrequency.WEEKLY: timedelta(weeks=1),
            BillFrequency.MONTHLY: timedelta(days=30),
            BillFrequency.QUARTERLY: timedelta(days=91),
            BillFrequency.YEARLY: timedelta(days=365),
        }

        paid_recurring = (
            db.query(Bill)
            .filter(
                and_(
                    Bill.status == BillStatus.PAID,
                    Bill.frequency != BillFrequency.ONE_TIME,
                )
            )
            .all()
        )

        created = 0
        for bill in paid_recurring:
            delta = frequency_delta.get(bill.frequency)
            if not delta:
                continue

            # Check if a future pending bill already exists for this series
            next_due = bill.due_date + delta
            existing = (
                db.query(Bill)
                .filter(
                    and_(
                        Bill.user_id == bill.user_id,
                        Bill.title == bill.title,
                        Bill.due_date == next_due,
                        Bill.status.in_([BillStatus.PENDING, BillStatus.DRAFT]),
                    )
                )
                .first()
            )
            if existing:
                continue

            new_bill = Bill(
                user_id=bill.user_id,
                title=bill.title,
                description=bill.description,
                amount=bill.amount,
                frequency=bill.frequency,
                vendor=bill.vendor,
                category=bill.category,
                notes=bill.notes,
                bill_date=bill.bill_date + delta,
                due_date=next_due,
                status=BillStatus.PENDING,
            )
            db.add(new_bill)
            created += 1

        if created:
            db.commit()
        return created


bill_service = BillService()
