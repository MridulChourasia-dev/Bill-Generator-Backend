import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service powered by Twilio."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                raise
        return self._client

    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send a plain SMS message via Twilio."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured. SMS not sent.")
            return False
        try:
            client = self._get_client()
            msg = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone,
            )
            logger.info(f"SMS sent to {to_phone}, SID: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False

    def send_bill_reminder_sms(
        self,
        to_phone: str,
        user_name: str,
        bill_title: str,
        amount: float,
        due_date: str,
    ) -> bool:
        message = (
            f"Hi {user_name}, reminder: '{bill_title}' of ${amount:,.2f} is due on {due_date}. "
            f"Please pay on time. - Bill Generator"
        )
        return self.send_sms(to_phone, message)

    def send_payment_confirmation_sms(
        self,
        to_phone: str,
        user_name: str,
        bill_title: str,
        amount: float,
    ) -> bool:
        message = (
            f"Hi {user_name}, your payment of ${amount:,.2f} for '{bill_title}' "
            f"has been confirmed. Thank you! - Bill Generator"
        )
        return self.send_sms(to_phone, message)

    def send_overdue_alert_sms(
        self,
        to_phone: str,
        user_name: str,
        bill_title: str,
        amount: float,
    ) -> bool:
        message = (
            f"⚠️ OVERDUE: Hi {user_name}, '{bill_title}' of ${amount:,.2f} is overdue. "
            f"Please pay immediately. - Bill Generator"
        )
        return self.send_sms(to_phone, message)


sms_service = SMSService()
