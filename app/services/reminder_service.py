from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.reminder import Reminder
from app.models.bill import Bill
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderListResponse


class ReminderService:
    """Service layer for creating and managing bill reminders."""

    def create_reminder(
        self, db: Session, user_id: UUID, data: ReminderCreate
    ) -> Reminder:
        # Verify the bill exists and belongs to user
        bill = db.query(Bill).filter(
            and_(Bill.id == data.bill_id, Bill.user_id == user_id)
        ).first()
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found",
            )

        reminder = Reminder(
            bill_id=data.bill_id,
            user_id=user_id,
            reminder_type=data.reminder_type,
            timing=data.timing,
            reminder_date=data.reminder_date,
            message=data.message,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder

    def get_reminders(
        self, db: Session, user_id: UUID, bill_id: UUID = None
    ) -> ReminderListResponse:
        query = db.query(Reminder).filter(Reminder.user_id == user_id)
        if bill_id:
            query = query.filter(Reminder.bill_id == bill_id)
        reminders = query.order_by(Reminder.reminder_date.asc()).all()
        return ReminderListResponse(reminders=reminders, total=len(reminders))

    def get_reminder_by_id(
        self, db: Session, reminder_id: UUID, user_id: UUID
    ) -> Reminder:
        reminder = db.query(Reminder).filter(
            and_(Reminder.id == reminder_id, Reminder.user_id == user_id)
        ).first()
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found",
            )
        return reminder

    def update_reminder(
        self,
        db: Session,
        reminder_id: UUID,
        user_id: UUID,
        data: ReminderUpdate,
    ) -> Reminder:
        reminder = self.get_reminder_by_id(db, reminder_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(reminder, field, value)
        db.commit()
        db.refresh(reminder)
        return reminder

    def delete_reminder(
        self, db: Session, reminder_id: UUID, user_id: UUID
    ) -> None:
        reminder = self.get_reminder_by_id(db, reminder_id, user_id)
        db.delete(reminder)
        db.commit()

    def get_pending_reminders(self, db: Session) -> List[Reminder]:
        """Fetch all unsent reminders whose time has arrived (for Celery tasks)."""
        now = datetime.now(timezone.utc)
        return (
            db.query(Reminder)
            .filter(
                and_(
                    Reminder.is_sent == False,  # noqa: E712
                    Reminder.reminder_date <= now,
                )
            )
            .all()
        )

    def mark_as_sent(self, db: Session, reminder: Reminder) -> None:
        reminder.is_sent = True
        reminder.sent_at = datetime.now(timezone.utc)
        db.commit()


reminder_service = ReminderService()
