from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

from app.models.bill import BillStatus, BillFrequency


class BillSortField(str, Enum):
    """Allowed sort fields for bills."""
    title = "title"
    amount = "amount"
    due_date = "due_date"
    bill_date = "bill_date"
    created_at = "created_at"
    status = "status"


class BillBase(BaseModel):
    title: str
    description: Optional[str] = None
    amount: Decimal
    frequency: BillFrequency = BillFrequency.ONE_TIME
    vendor: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    bill_date: datetime
    due_date: datetime

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        if v > Decimal("99999999999.99"):
            raise ValueError("Amount exceeds maximum allowed value")
        return round(v, 2)

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime, info) -> datetime:
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Title cannot be empty")
        if len(v) > 255:
            raise ValueError("Title must not exceed 255 characters")
        return v


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[BillStatus] = None
    frequency: Optional[BillFrequency] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    bill_date: Optional[datetime] = None
    due_date: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2) if v is not None else v


class MarkAsPaidRequest(BaseModel):
    paid_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None


class BillCloneRequest(BaseModel):
    """Optional overrides when cloning a bill."""
    title: Optional[str] = None
    bill_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class BulkBillActionRequest(BaseModel):
    """Request body for bulk operations on bills."""
    bill_ids: List[UUID]
    action: str  # "delete", "cancel", "mark_paid"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"delete", "cancel", "mark_paid"}
        if v not in allowed:
            raise ValueError(f"Action must be one of: {', '.join(allowed)}")
        return v

    @field_validator("bill_ids")
    @classmethod
    def validate_bill_ids(cls, v: List[UUID]) -> List[UUID]:
        if not v:
            raise ValueError("At least one bill ID is required")
        if len(v) > 100:
            raise ValueError("Cannot process more than 100 bills at once")
        return v


class BillResponse(BillBase):
    id: UUID
    user_id: UUID
    status: BillStatus
    paid_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BillListResponse(BaseModel):
    bills: List[BillResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BillStatsResponse(BaseModel):
    """Statistics summary for bills."""
    total_count: int
    pending_count: int
    paid_count: int
    overdue_count: int
    cancelled_count: int
    draft_count: int
    total_amount: float
    pending_amount: float
    paid_amount: float
    overdue_amount: float
