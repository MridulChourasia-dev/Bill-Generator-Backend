from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentBase(BaseModel):
    amount: Decimal
    payment_method: PaymentMethod = PaymentMethod.CASH
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    payment_date: datetime

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)


class PaymentCreate(PaymentBase):
    bill_id: UUID


class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = None
    payment_method: Optional[PaymentMethod] = None
    status: Optional[PaymentStatus] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[datetime] = None


class PaymentResponse(PaymentBase):
    id: UUID
    bill_id: UUID
    user_id: UUID
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
