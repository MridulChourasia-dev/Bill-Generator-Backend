import logging
from datetime import datetime, timezone, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.reminder import Reminder
from app.services.report_service import report_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.report_tasks.generate_monthly_report", bind=True)
def generate_monthly_report(self):
    """
    Scheduled task: runs on the 1st of each month at 8am UTC.
    Generates a monthly PDF report for each user and optionally emails it.
    """
    db = SessionLocal()
    try:
        from app.models.user import User
        from app.services.pdf_service import pdf_service
        import asyncio
        from app.services.email_service import email_service

        now = datetime.now(timezone.utc)
        last_month = now.replace(day=1) - timedelta(days=1)
        period = last_month.strftime("%B %Y")

        users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
        reports_generated = 0

        for user in users:
            try:
                stats = report_service.get_dashboard_stats(db, user.id)
                pdf_path = pdf_service.generate_report(
                    user_name=user.full_name or user.username,
                    report_period=period,
                    total_bills=stats["total_bills"],
                    paid_bills=stats["paid_bills"],
                    overdue_bills=stats["overdue_bills"],
                    total_amount_due=stats["total_amount_due"],
                    total_amount_paid=stats["total_amount_paid"],
                )
                if user.email_notifications:
                    asyncio.run(
                        email_service.send_receipt(
                            to_email=user.email,
                            user_name=user.full_name or user.username,
                            bill_title=f"Monthly Report - {period}",
                            amount=stats["total_amount_paid"],
                            pdf_path=pdf_path,
                        )
                    )
                reports_generated += 1
            except Exception as e:
                logger.error(f"Failed to generate report for user {user.id}: {e}")

        logger.info(f"Generated {reports_generated} monthly reports for {period}.")
        return {"reports_generated": reports_generated, "period": period}
    finally:
        db.close()


@celery_app.task(name="app.tasks.report_tasks.clean_old_data", bind=True)
def clean_old_data(self):
    """
    Scheduled task: runs weekly (Sunday midnight).
    Deletes sent reminders older than 90 days to keep the database clean.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        deleted = (
            db.query(Reminder)
            .filter(Reminder.is_sent == True, Reminder.sent_at < cutoff)  # noqa: E712
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Cleaned up {deleted} old sent reminders.")
        return {"deleted_reminders": deleted}
    except Exception as exc:
        db.rollback()
        logger.error(f"clean_old_data task failed: {exc}")
        raise
    finally:
        db.close()
