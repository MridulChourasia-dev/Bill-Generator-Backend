from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class ReminderType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"


class ReminderTiming(str, enum.Enum):
    ONE_DAY_BEFORE = "1_day_before"
    THREE_DAYS_BEFORE = "3_days_before"
    SEVEN_DAYS_BEFORE = "7_days_before"
    ON_DUE_DATE = "on_due_date"
    ONE_DAY_AFTER = "1_day_after"
    CUSTOM = "custom"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    reminder_type = Column(SAEnum(ReminderType), default=ReminderType.EMAIL, nullable=False)
    timing = Column(SAEnum(ReminderTiming), default=ReminderTiming.ONE_DAY_BEFORE)
    reminder_date = Column(DateTime(timezone=True), nullable=False)

    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    message = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    bill = relationship("Bill", back_populates="reminders")
    user = relationship("User", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder(id={self.id}, bill_id={self.bill_id}, type={self.reminder_type}, sent={self.is_sent})>"
