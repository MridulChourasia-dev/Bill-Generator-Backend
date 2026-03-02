"""
Seed script: populates the database with sample data for development.
Run: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.bill import Bill, BillStatus, BillFrequency
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.reminder import Reminder, ReminderType, ReminderTiming
from app.services.auth_service import hash_password

# Import all models
import app.models.user  # noqa
import app.models.bill  # noqa
import app.models.payment  # noqa
import app.models.reminder  # noqa


def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already has data. Skipping seed.")
            return

        print("Creating demo user...")
        user = User(
            email="demo@billgenerator.com",
            username="demouser",
            hashed_password=hash_password("DemoPass123"),
            full_name="Demo User",
            phone="+1234567890",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()

        now = datetime.now(timezone.utc)

        print("Creating sample bills...")
        bills_data = [
            {
                "title": "Electricity Bill",
                "amount": Decimal("120.50"),
                "vendor": "Power Corp",
                "category": "Utilities",
                "frequency": BillFrequency.MONTHLY,
                "bill_date": now - timedelta(days=5),
                "due_date": now + timedelta(days=10),
                "status": BillStatus.PENDING,
            },
            {
                "title": "Internet Subscription",
                "amount": Decimal("59.99"),
                "vendor": "FastNet ISP",
                "category": "Internet",
                "frequency": BillFrequency.MONTHLY,
                "bill_date": now - timedelta(days=10),
                "due_date": now + timedelta(days=5),
                "status": BillStatus.PENDING,
            },
            {
                "title": "Water Bill",
                "amount": Decimal("45.00"),
                "vendor": "City Water",
                "category": "Utilities",
                "frequency": BillFrequency.MONTHLY,
                "bill_date": now - timedelta(days=30),
                "due_date": now - timedelta(days=10),
                "status": BillStatus.PAID,
                "paid_date": now - timedelta(days=12),
            },
            {
                "title": "Gym Membership",
                "amount": Decimal("35.00"),
                "vendor": "FitLife Gym",
                "category": "Health",
                "frequency": BillFrequency.MONTHLY,
                "bill_date": now - timedelta(days=35),
                "due_date": now - timedelta(days=5),
                "status": BillStatus.OVERDUE,
            },
            {
                "title": "Annual Software License",
                "amount": Decimal("299.00"),
                "vendor": "TechSoft Inc.",
                "category": "Software",
                "frequency": BillFrequency.YEARLY,
                "bill_date": now - timedelta(days=2),
                "due_date": now + timedelta(days=30),
                "status": BillStatus.PENDING,
            },
        ]

        created_bills = []
        for bd in bills_data:
            bill = Bill(user_id=user.id, **bd)
            db.add(bill)
            created_bills.append(bill)
        db.flush()

        print("Creating sample payments...")
        paid_bill = created_bills[2]  # Water Bill (paid)
        payment = Payment(
            bill_id=paid_bill.id,
            user_id=user.id,
            amount=Decimal("45.00"),
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            reference_number="PAY-2024-001",
            payment_date=now - timedelta(days=12),
        )
        db.add(payment)

        print("Creating sample reminders...")
        pending_bill = created_bills[0]  # Electricity Bill
        reminder = Reminder(
            bill_id=pending_bill.id,
            user_id=user.id,
            reminder_type=ReminderType.EMAIL,
            timing=ReminderTiming.THREE_DAYS_BEFORE,
            reminder_date=pending_bill.due_date - timedelta(days=3),
        )
        db.add(reminder)

        db.commit()
        print("✅ Seed data created successfully!")
        print(f"   Demo credentials: demo@billgenerator.com / DemoPass123")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
