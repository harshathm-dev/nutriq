import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger("nutriq.email")

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "email_templates"))


class EmailService:
    @staticmethod
    def _load_template(template_name: str, context: dict) -> str:
        """Load an HTML template and interpolate context variables."""
        template_path = os.path.join(TEMPLATES_DIR, template_name)
        if not os.path.exists(template_path):
            logger.warning(f"Email template not found at {template_path}")
            return ""
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            for key, val in context.items():
                content = content.replace(f"{{{key}}}", str(val))
            return content
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return ""

    @classmethod
    def _send_email(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_fallback: str
    ) -> bool:
        """
        Send an email via SMTP or log in development mode.
        Failure never raises an exception so authentication is never blocked.
        """
        try:
            if not to_email or "@" not in to_email:
                logger.warning(f"Invalid recipient email address: {to_email}")
                return False

            # If SMTP is not configured, operate in development/mock mode safely
            if not settings.SMTP_HOST or settings.EMAIL_PROVIDER in ["console", "mock"]:
                logger.info(
                    f"[Email Service: Dev/Mock Mode] Email to: {to_email} | Subject: '{subject}'"
                )
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to_email

            # Attach plain text and HTML versions
            msg.attach(MIMEText(plain_text_fallback, "plain", "utf-8"))
            if html_content:
                msg.attach(MIMEText(html_content, "html", "utf-8"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email successfully delivered to {to_email} (Subject: '{subject}')")
            return True
        except Exception as e:
            # Secure error logging: never expose credentials or crash caller
            logger.warning(f"Email delivery failed for {to_email}: {type(e).__name__} - {str(e)}")
            return False

    @classmethod
    def send_welcome_email(cls, to_email: str, user_name: Optional[str] = None) -> bool:
        """Send welcome email to newly registered user."""
        try:
            display_name = user_name.strip() if (user_name and user_name.strip()) else to_email.split("@")[0]
            subject = "Welcome to NutriQ!"
            
            context = {
                "user_name": display_name,
                "app_url": settings.APP_URL,
            }
            
            html_content = cls._load_template("welcome.html", context)
            plain_text = (
                f"Hi {display_name},\n\n"
                f"Welcome to NutriQ!\n\n"
                f"Your NutriQ account has been successfully created.\n\n"
                f"NutriQ helps you track your meals, calories, nutrition, progress, and personal goals.\n\n"
                f"Complete your profile to start using personalized nutrition features.\n\n"
                f"Open NutriQ: {settings.APP_URL}\n\n"
                f"If you did not create this account, please secure your account and contact NutriQ support.\n\n"
                f"Regards,\nNutriQ Team"
            )

            return cls._send_email(to_email, subject, html_content, plain_text)
        except Exception as e:
            logger.warning(f"send_welcome_email caught error: {e}")
            return False

    @classmethod
    def send_login_notification(
        cls,
        to_email: str,
        user_name: Optional[str] = None,
        login_time: Optional[datetime] = None
    ) -> bool:
        """Send login notification email with actual login date/time."""
        try:
            display_name = user_name.strip() if (user_name and user_name.strip()) else to_email.split("@")[0]
            dt = login_time or datetime.now(timezone.utc)
            
            # Format date and time dynamically (e.g. August 19, 2026 and 14:25 UTC)
            login_date = dt.strftime("%B %d, %Y")
            login_time_str = dt.strftime("%I:%M %p UTC")

            subject = "New login to your NutriQ account"
            context = {
                "user_name": display_name,
                "login_date": login_date,
                "login_time": login_time_str,
                "app_url": settings.APP_URL,
            }

            html_content = cls._load_template("login_notification.html", context)
            plain_text = (
                f"Hi {display_name},\n\n"
                f"You have successfully logged in to your NutriQ account.\n\n"
                f"Login details:\n"
                f"Date: {login_date}\n"
                f"Time: {login_time_str}\n\n"
                f"Open NutriQ: {settings.APP_URL}\n\n"
                f"If you did not perform this login, please secure your account immediately.\n\n"
                f"Regards,\nNutriQ Team"
            )

            return cls._send_email(to_email, subject, html_content, plain_text)
        except Exception as e:
            logger.warning(f"send_login_notification caught error: {e}")
            return False

    @classmethod
    def send_password_reset_email(
        cls,
        to_email: str,
        user_name: Optional[str] = None,
        reset_token: str = ""
    ) -> bool:
        """Send secure password reset link email."""
        try:
            display_name = user_name.strip() if (user_name and user_name.strip()) else to_email.split("@")[0]
            reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"
            expire_minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES

            subject = "Reset your NutriQ password"
            context = {
                "user_name": display_name,
                "reset_url": reset_url,
                "expire_minutes": expire_minutes,
            }

            html_content = cls._load_template("password_reset.html", context)
            plain_text = (
                f"Hi {display_name},\n\n"
                f"We received a request to reset your NutriQ account password.\n\n"
                f"Click the link below to create a new password:\n"
                f"{reset_url}\n\n"
                f"This password reset link will expire in {expire_minutes} minutes and can only be used once.\n\n"
                f"If you did not request a password reset, you can safely ignore this email.\n\n"
                f"Regards,\nNutriQ Team"
            )

            return cls._send_email(to_email, subject, html_content, plain_text)
        except Exception as e:
            logger.warning(f"send_password_reset_email caught error: {e}")
            return False

    @classmethod
    def send_google_only_notice_email(
        cls,
        to_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """Send notice to Google-only users attempting password reset."""
        try:
            display_name = user_name.strip() if (user_name and user_name.strip()) else to_email.split("@")[0]
            subject = "Google Sign-In Account Notice"
            context = {
                "user_name": display_name,
                "app_url": settings.APP_URL,
            }

            html_content = cls._load_template("google_notice.html", context)
            plain_text = (
                f"Hi {display_name},\n\n"
                f"We received a password reset request for your NutriQ account.\n\n"
                f"This account uses Google Sign-In. Please continue with Google to access your account: {settings.APP_URL}/login\n\n"
                f"If you did not make this request, you can safely disregard this email.\n\n"
                f"Regards,\nNutriQ Team"
            )

            return cls._send_email(to_email, subject, html_content, plain_text)
        except Exception as e:
            logger.warning(f"send_google_only_notice_email caught error: {e}")
            return False
