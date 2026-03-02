from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.reminder import ReminderType, ReminderTiming


class ReminderBase(BaseModel):
    bill_id: UUID
    reminder_type: ReminderType = ReminderType.EMAIL
    timing: ReminderTiming = ReminderTiming.ONE_DAY_BEFORE
    reminder_date: datetime
    message: Optional[str] = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    reminder_type: Optional[ReminderType] = None
    timing: Optional[ReminderTiming] = None
    reminder_date: Optional[datetime] = None
    message: Optional[str] = None


class ReminderResponse(ReminderBase):
    id: UUID
    user_id: UUID
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    reminders: List[ReminderResponse]
    total: int
