from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderResponse, ReminderListResponse
from app.services.reminder_service import reminder_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new reminder for a bill."""
    return reminder_service.create_reminder(db, current_user.id, data)


@router.get("/", response_model=ReminderListResponse)
def get_reminders(
    bill_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all reminders, optionally filtered by bill."""
    return reminder_service.get_reminders(db, current_user.id, bill_id=bill_id)


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific reminder by ID."""
    return reminder_service.get_reminder_by_id(db, reminder_id, current_user.id)


@router.put("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: UUID,
    data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a reminder."""
    return reminder_service.update_reminder(db, reminder_id, current_user.id, data)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a reminder."""
    reminder_service.delete_reminder(db, reminder_id, current_user.id)
