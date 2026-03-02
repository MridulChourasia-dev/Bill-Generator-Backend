from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.bill import BillStatus, BillFrequency


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
        return round(v, 2)

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime, info) -> datetime:
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


class MarkAsPaidRequest(BaseModel):
    paid_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None


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
