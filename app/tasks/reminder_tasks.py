import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.reminder import ReminderType
from app.services.reminder_service import reminder_service
from app.services.bill_service import bill_service
from app.services.email_service import email_service
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.reminder_tasks.send_bill_reminders", bind=True, max_retries=3)
def send_bill_reminders(self):
    """
    Scheduled task: runs every 5 minutes.
    Finds all pending reminders whose time has passed and sends emails/SMS.
    """
    db = SessionLocal()
    sent_count = 0
    try:
        pending = reminder_service.get_pending_reminders(db)
        logger.info(f"Found {len(pending)} pending reminders to send.")

        for reminder in pending:
            bill = reminder.bill
            user = reminder.user
            try:
                if reminder.reminder_type in (ReminderType.EMAIL, ReminderType.BOTH):
                    import asyncio
                    asyncio.run(
                        email_service.send_bill_reminder(
                            to_email=user.email,
                            user_name=user.full_name or user.username,
                            bill_title=bill.title,
                            amount=float(bill.amount),
                            due_date=bill.due_date.strftime("%d %b %Y"),
                        )
                    )

                if reminder.reminder_type in (ReminderType.SMS, ReminderType.BOTH):
                    if user.phone:
                        sms_service.send_bill_reminder_sms(
                            to_phone=user.phone,
                            user_name=user.full_name or user.username,
                            bill_title=bill.title,
                            amount=float(bill.amount),
                            due_date=bill.due_date.strftime("%d %b %Y"),
                        )

                reminder_service.mark_as_sent(db, reminder)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending reminder {reminder.id}: {e}")

        logger.info(f"Sent {sent_count} reminders.")
        return {"sent": sent_count}
    except Exception as exc:
        logger.error(f"send_bill_reminders task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(name="app.tasks.reminder_tasks.mark_overdue_bills", bind=True, max_retries=3)
def mark_overdue_bills(self):
    """
    Scheduled task: runs every hour.
    Marks all pending bills with past due dates as OVERDUE.
    """
    db = SessionLocal()
    try:
        count = bill_service.mark_overdue_bills(db)
        logger.info(f"Marked {count} bills as overdue.")
        return {"marked_overdue": count}
    except Exception as exc:
        logger.error(f"mark_overdue_bills task failed: {exc}")
        raise self.retry(exc=exc, countdown=120)
    finally:
        db.close()
