import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Async email service using aiosmtplib."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_name = settings.EMAILS_FROM_NAME
        self.from_email = settings.EMAILS_FROM_EMAIL

    async def _send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: Optional[List[Path]] = None,
    ) -> bool:
        """Internal method to send an email with optional attachments."""
        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        if attachments:
            for file_path in attachments:
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={file_path.name}",
                    )
                    message.attach(part)

        try:
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=False,
                start_tls=True,
            ) as smtp:
                await smtp.login(self.username, self.password)
                await smtp.send_message(message)
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_bill_reminder(
        self, to_email: str, user_name: str, bill_title: str, amount: float, due_date: str
    ) -> bool:
        subject = f"🔔 Reminder: {bill_title} due on {due_date}"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Bill Reminder</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>This is a reminder that your bill <strong>{bill_title}</strong>
               amounting to <strong>${amount:,.2f}</strong> is due on <strong>{due_date}</strong>.</p>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Bill:</strong> {bill_title}</p>
                <p><strong>Amount Due:</strong> ${amount:,.2f}</p>
                <p><strong>Due Date:</strong> {due_date}</p>
            </div>
            <p>Please ensure timely payment to avoid any late fees.</p>
            <p>Regards,<br>The Bill Generator Team</p>
        </div>
        """
        return await self._send(to_email, subject, html_body)

    async def send_payment_confirmation(
        self, to_email: str, user_name: str, bill_title: str, amount: float, payment_date: str
    ) -> bool:
        subject = f"✅ Payment Confirmed: {bill_title}"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #27ae60;">Payment Confirmed!</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Your payment for <strong>{bill_title}</strong> of <strong>${amount:,.2f}</strong>
               has been recorded on <strong>{payment_date}</strong>.</p>
            <div style="background: #d5f4e6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p>✅ <strong>Bill:</strong> {bill_title}</p>
                <p>💰 <strong>Amount Paid:</strong> ${amount:,.2f}</p>
                <p>📅 <strong>Payment Date:</strong> {payment_date}</p>
            </div>
            <p>Thank you for your prompt payment!</p>
            <p>Regards,<br>The Bill Generator Team</p>
        </div>
        """
        return await self._send(to_email, subject, html_body)

    async def send_receipt(
        self,
        to_email: str,
        user_name: str,
        bill_title: str,
        amount: float,
        pdf_path: Optional[Path] = None,
    ) -> bool:
        subject = f"📄 Receipt: {bill_title}"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2980b9;">Payment Receipt</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Please find attached the receipt for your payment of <strong>${amount:,.2f}</strong>
               for <strong>{bill_title}</strong>.</p>
            <p>Regards,<br>The Bill Generator Team</p>
        </div>
        """
        attachments = [pdf_path] if pdf_path else None
        return await self._send(to_email, subject, html_body, attachments)

    async def send_verification_email(
        self, to_email: str, user_name: str, verification_token: str
    ) -> bool:
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        subject = "📧 Verify Your Email - Bill Generator"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Welcome to Bill Generator!</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}"
                   style="background: #3498db; color: white; padding: 14px 30px;
                          text-decoration: none; border-radius: 6px; font-size: 16px;">
                    Verify Email
                </a>
            </div>
            <p>This link expires in 24 hours.</p>
            <p>Regards,<br>The Bill Generator Team</p>
        </div>
        """
        return await self._send(to_email, subject, html_body)

    async def send_password_reset_email(
        self, to_email: str, user_name: str, reset_token: str
    ) -> bool:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "🔑 Password Reset Request - Bill Generator"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #e74c3c;">Password Reset</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>We received a request to reset your password. Click the button below to proceed:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}"
                   style="background: #e74c3c; color: white; padding: 14px 30px;
                          text-decoration: none; border-radius: 6px; font-size: 16px;">
                    Reset Password
                </a>
            </div>
            <p>This link expires in 1 hour. If you did not request a password reset, please ignore this email.</p>
            <p>Regards,<br>The Bill Generator Team</p>
        </div>
        """
        return await self._send(to_email, subject, html_body)


email_service = EmailService()
