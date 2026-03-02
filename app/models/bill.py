from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class BillStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DRAFT = "draft"


class BillFrequency(str, enum.Enum):
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Bill(Base):
    __tablename__ = "bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    status = Column(SAEnum(BillStatus), default=BillStatus.PENDING, nullable=False, index=True)
    frequency = Column(SAEnum(BillFrequency), default=BillFrequency.ONE_TIME, nullable=False)

    vendor = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    notes = Column(String(2000), nullable=True)

    bill_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="bills")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="bill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bill(id={self.id}, title={self.title}, amount={self.amount}, status={self.status})>"
