from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.bill import Bill, BillStatus
from app.models.payment import Payment
from app.models.user import User


class ReportService:
    """Service for generating statistical reports and dashboard data."""

    def get_dashboard_stats(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Aggregate statistics for the user's dashboard."""
        now = datetime.now(timezone.utc)

        # Bill counts
        total_bills = db.query(func.count(Bill.id)).filter(Bill.user_id == user_id).scalar()
        paid_bills = db.query(func.count(Bill.id)).filter(
            and_(Bill.user_id == user_id, Bill.status == BillStatus.PAID)
        ).scalar()
        overdue_bills = db.query(func.count(Bill.id)).filter(
            and_(Bill.user_id == user_id, Bill.status == BillStatus.OVERDUE)
        ).scalar()
        pending_bills = db.query(func.count(Bill.id)).filter(
            and_(Bill.user_id == user_id, Bill.status == BillStatus.PENDING)
        ).scalar()

        # Amount totals
        total_amount_due = db.query(func.sum(Bill.amount)).filter(
            and_(Bill.user_id == user_id, Bill.status.in_([BillStatus.PENDING, BillStatus.OVERDUE]))
        ).scalar() or Decimal("0.00")

        total_amount_paid = db.query(func.sum(Payment.amount)).filter(
            Payment.user_id == user_id
        ).scalar() or Decimal("0.00")

        # Upcoming bills (due within 7 days)
        from datetime import timedelta
        seven_days_later = now + timedelta(days=7)
        upcoming_bills = (
            db.query(Bill)
            .filter(
                and_(
                    Bill.user_id == user_id,
                    Bill.due_date >= now,
                    Bill.due_date <= seven_days_later,
                    Bill.status == BillStatus.PENDING,
                )
            )
            .order_by(Bill.due_date.asc())
            .limit(5)
            .all()
        )

        return {
            "total_bills": total_bills,
            "paid_bills": paid_bills,
            "overdue_bills": overdue_bills,
            "pending_bills": pending_bills,
            "total_amount_due": float(total_amount_due),
            "total_amount_paid": float(total_amount_paid),
            "upcoming_bills": [
                {
                    "id": str(b.id),
                    "title": b.title,
                    "amount": float(b.amount),
                    "due_date": b.due_date.isoformat(),
                    "status": b.status.value,
                }
                for b in upcoming_bills
            ],
        }

    def get_bill_report(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Bills grouped by status and category."""
        by_status = (
            db.query(Bill.status, func.count(Bill.id), func.sum(Bill.amount))
            .filter(Bill.user_id == user_id)
            .group_by(Bill.status)
            .all()
        )

        by_category = (
            db.query(Bill.category, func.count(Bill.id), func.sum(Bill.amount))
            .filter(and_(Bill.user_id == user_id, Bill.category.isnot(None)))
            .group_by(Bill.category)
            .all()
        )

        return {
            "by_status": [
                {
                    "status": row[0].value,
                    "count": row[1],
                    "total_amount": float(row[2] or 0),
                }
                for row in by_status
            ],
            "by_category": [
                {
                    "category": row[0],
                    "count": row[1],
                    "total_amount": float(row[2] or 0),
                }
                for row in by_category
            ],
        }

    def get_payment_report(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Payments grouped by method and monthly summary."""
        by_method = (
            db.query(Payment.payment_method, func.count(Payment.id), func.sum(Payment.amount))
            .filter(Payment.user_id == user_id)
            .group_by(Payment.payment_method)
            .all()
        )

        monthly = (
            db.query(
                func.date_trunc("month", Payment.payment_date).label("month"),
                func.count(Payment.id),
                func.sum(Payment.amount),
            )
            .filter(Payment.user_id == user_id)
            .group_by("month")
            .order_by("month")
            .all()
        )

        return {
            "by_method": [
                {
                    "method": row[0].value,
                    "count": row[1],
                    "total_amount": float(row[2] or 0),
                }
                for row in by_method
            ],
            "monthly_summary": [
                {
                    "month": row[0].strftime("%Y-%m") if row[0] else None,
                    "count": row[1],
                    "total_amount": float(row[2] or 0),
                }
                for row in monthly
            ],
        }

    def get_analytics(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Chart-ready analytics data combining bill and payment trends."""
        dashboard = self.get_dashboard_stats(db, user_id)
        bill_report = self.get_bill_report(db, user_id)
        payment_report = self.get_payment_report(db, user_id)

        payment_rate = (
            (dashboard["paid_bills"] / dashboard["total_bills"] * 100)
            if dashboard["total_bills"] > 0
            else 0.0
        )

        return {
            "summary": dashboard,
            "bill_breakdown": bill_report,
            "payment_breakdown": payment_report,
            "payment_rate_percent": round(payment_rate, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


report_service = ReportService()
