import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

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
    def _send_email_detailed(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_fallback: str
    ) -> Dict[str, Any]:
        """
        Send an email via Resend API, SMTP, or log in development/mock mode.
        Returns a diagnostic dictionary with delivery details and error descriptions.
        Failure never raises an exception to prevent interrupting authentication.
        """
        clean_to = to_email.strip() if to_email else ""
        from_email = getattr(settings, "WELCOME_EMAIL_FROM", None) or getattr(settings, "EMAIL_FROM", None) or "NutriQ <onboarding@resend.dev>"
        provider = (getattr(settings, "EMAIL_PROVIDER", "resend") or "resend").lower().strip()

        if not clean_to or "@" not in clean_to:
            err_msg = f"Invalid recipient email address: {clean_to}"
            logger.warning(err_msg)
            return {
                "success": False,
                "id": None,
                "error": err_msg,
                "provider": provider,
                "from": from_email,
                "to": clean_to
            }

        # 1. Resend API Delivery
        if provider == "resend" or settings.RESEND_API_KEY:
            if not settings.RESEND_API_KEY:
                err_msg = (
                    "Configuration Error: EMAIL_PROVIDER is set to 'resend', but RESEND_API_KEY is missing "
                    "or empty in .env. Please configure RESEND_API_KEY in nutriq-backend/.env"
                )
                logger.error(err_msg)
                return {
                    "success": False,
                    "id": None,
                    "error": err_msg,
                    "provider": "resend",
                    "from": from_email,
                    "to": clean_to
                }

            try:
                import resend
                resend.api_key = settings.RESEND_API_KEY
                logger.info(f"Welcome email requested for user: {clean_to}")

                params = {
                    "from": from_email,
                    "to": [clean_to],
                    "subject": subject,
                    "html": html_content or plain_text_fallback,
                    "text": plain_text_fallback,
                }
                res = resend.Emails.send(params)
                res_id = getattr(res, "id", None) or (res.get("id") if isinstance(res, dict) else str(res))
                logger.info(f"Resend email ID: {res_id}")
                return {
                    "success": True,
                    "id": str(res_id),
                    "error": None,
                    "provider": "resend",
                    "from": from_email,
                    "to": clean_to
                }
            except Exception as resend_err:
                err_str = f"{type(resend_err).__name__} - {str(resend_err)}"
                logger.error(f"Welcome email failed: {err_str}")
                # If SMTP is configured as backup, attempt fallback; otherwise return diagnostic failure
                if settings.SMTP_HOST and provider not in ["console", "mock"]:
                    logger.info(f"Attempting fallback to SMTP for {clean_to}...")
                else:
                    return {
                        "success": False,
                        "id": None,
                        "error": err_str,
                        "provider": "resend",
                        "from": from_email,
                        "to": clean_to
                    }

        # 2. SMTP Delivery if configured
        if settings.SMTP_HOST and provider in ["smtp", "live"]:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = from_email
                msg["To"] = clean_to

                msg.attach(MIMEText(plain_text_fallback, "plain", "utf-8"))
                if html_content:
                    msg.attach(MIMEText(html_content, "html", "utf-8"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_USE_TLS:
                        server.starttls()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)

                logger.info(f"Email successfully delivered via SMTP to {clean_to} (Subject: '{subject}')")
                return {
                    "success": True,
                    "id": "smtp_dispatched",
                    "error": None,
                    "provider": "smtp",
                    "from": from_email,
                    "to": clean_to
                }
            except Exception as smtp_err:
                err_str = f"{type(smtp_err).__name__} - {str(smtp_err)}"
                logger.error(f"SMTP delivery failed: {err_str}")
                return {
                    "success": False,
                    "id": None,
                    "error": err_str,
                    "provider": "smtp",
                    "from": from_email,
                    "to": clean_to
                }

        # 3. Development / Mock / Console Mode fallback
        logger.info(f"[Email Service: Dev/Mock Mode] Email to: {clean_to} | Subject: '{subject}'")
        return {
            "success": True,
            "id": "mock_id",
            "error": None,
            "provider": "mock",
            "from": from_email,
            "to": clean_to
        }

    @classmethod
    def _send_email(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_fallback: str
    ) -> bool:
        """Helper returning boolean success for backward compatibility."""
        result = cls._send_email_detailed(to_email, subject, html_content, plain_text_fallback)
        return bool(result.get("success"))

    @classmethod
    def send_welcome_email(cls, to_email: str, user_name: Optional[str] = None) -> bool:
        """Send welcome email to newly registered or first-time Google user."""
        try:
            display_name = user_name.strip() if (user_name and user_name.strip()) else to_email.split("@")[0]
            subject = "Welcome to NutriQ! 🌱"
            
            context = {
                "user_name": display_name,
                "app_url": settings.APP_URL,
            }
            
            html_content = cls._load_template("welcome.html", context)
            plain_text = (
                f"Hi {display_name},\n\n"
                f"Welcome to NutriQ!\n\n"
                f"Your personal nutrition intelligence journey starts here.\n\n"
                f"NutriQ helps you track:\n"
                f"• Calories\n"
                f"• Protein\n"
                f"• Hydration\n"
                f"• Meals\n"
                f"• Weight goals\n"
                f"• Nutrition insights\n\n"
                f"Thank you for joining NutriQ.\n\n"
                f"Best regards,\n"
                f"The NutriQ Team"
            )

            return cls._send_email(to_email, subject, html_content, plain_text)
        except Exception as e:
            logger.warning(f"send_welcome_email caught error for {to_email}: {e}")
            return False

    @classmethod
    def send_test_email(cls, to_email: str) -> Dict[str, Any]:
        """Send development/diagnostic test welcome email and return detailed result."""
        try:
            display_name = to_email.split("@")[0]
            subject = "Welcome to NutriQ!"
            
            context = {
                "user_name": display_name,
                "app_url": settings.APP_URL,
            }
            
            html_content = cls._load_template("welcome.html", context)
            plain_text = (
                f"Welcome to NutriQ!\n\n"
                f"Your personal nutrition intelligence journey starts here.\n\n"
                f"NutriQ helps you track:\n"
                f"• Calories\n"
                f"• Protein\n"
                f"• Hydration\n"
                f"• Meals\n"
                f"• Weight goals\n"
                f"• Nutrition insights\n\n"
                f"Thank you for joining NutriQ."
            )

            return cls._send_email_detailed(to_email, subject, html_content, plain_text)
        except Exception as e:
            err_str = f"{type(e).__name__} - {str(e)}"
            logger.error(f"send_test_email caught error for {to_email}: {err_str}")
            return {
                "success": False,
                "id": None,
                "error": err_str,
                "provider": getattr(settings, "EMAIL_PROVIDER", "resend"),
                "from": getattr(settings, "WELCOME_EMAIL_FROM", "NutriQ <onboarding@resend.dev>"),
                "to": to_email
            }

    @classmethod
    async def send_welcome_email_and_update_status(
        cls,
        user_id: str,
        to_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Attempts to send the welcome email in background and updates User.welcome_email_sent = True upon success.
        If email delivery fails, logs error, leaves welcome_email_sent = False, and never raises exceptions.
        """
        try:
            if not user_id or not to_email:
                return False

            success = cls.send_welcome_email(to_email, user_name)
            if success:
                try:
                    from app.database.session import AsyncSessionLocal
                    from app.models.user import User
                    from sqlalchemy import select
                    async with AsyncSessionLocal() as session:
                        res = await session.execute(select(User).where(User.id == user_id))
                        user = res.scalar_one_or_none()
                        if user and not user.welcome_email_sent:
                            user.welcome_email_sent = True
                            await session.commit()
                            logger.info(f"Updated welcome_email_sent=True for user_id={user_id} ({to_email})")
                except Exception as db_err:
                    logger.warning(f"Failed to update welcome_email_sent status in DB for user_id={user_id}: {db_err}")
                return True
            else:
                logger.warning(f"Welcome email delivery failed for user_id={user_id} ({to_email}), welcome_email_sent remains False")
                return False
        except Exception as e:
            logger.warning(f"send_welcome_email_and_update_status caught error for user_id={user_id}: {e}")
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
            
            # Format date and time dynamically (e.g. August 21, 2026 and 02:25 PM UTC)
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
