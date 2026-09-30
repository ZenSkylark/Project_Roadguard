from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from ..config import settings


def _get_email_mode() -> str:
    """Read the current email mode from system settings."""
    try:
        from .templates import load_ui_settings
        return load_ui_settings().get("email_mode", "dev")
    except Exception:
        return "dev"


def send_email(to: str, subject: str, body: str):
    """Route email to DEV console, Mailtrap sandbox, or Resend live delivery."""
    mode = _get_email_mode()

    # DEV MODE — print to backend console
    if mode == "dev":
        print("\n" + "=" * 50)
        print(f"📧 [DEV EMAIL] To: {to}")
        print(f"📧 [DEV EMAIL] Subject: {subject}")
        print(f"📧 [DEV EMAIL] Body:\n{body}")
        print("=" * 50 + "\n")
        return

    # MAILTRAP MODE — capture in sandbox inbox
    if mode == "mailtrap":
        _send_mailtrap(to, subject, body)
        return

    # RESEND MODE — real delivery
    if mode == "resend":
        _send_resend(to, subject, body)
        return

    # Fallback for unknown modes
    print(f"⚠️ Unknown email mode: {mode}, falling back to DEV")
    print(f"📧 [DEV EMAIL] To: {to}\n📧 [DEV EMAIL] Body:\n{body}")


def _send_mailtrap(to: str, subject: str, body: str):
    """Send via Mailtrap sandbox SMTP (emails appear in Mailtrap web inbox)."""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.MAILTRAP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
            server.login(settings.MAILTRAP_USERNAME, settings.MAILTRAP_PASSWORD)
            server.send_message(msg)
        print(f"✅ [MAILTRAP] Email captured in sandbox for {to}")
    except Exception as e:
        print(f"❌ [MAILTRAP] Failed to send email to {to}: {e}")


def _send_resend(to: str, subject: str, body: str):
    """Send via Resend SMTP (real delivery to recipient inbox)."""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.RESEND_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Resend uses port 465 with SSL
        with smtplib.SMTP_SSL("smtp.resend.com", 465) as server:
            server.login("resend", settings.RESEND_API_KEY)
            server.send_message(msg)
        print(f"✅ [RESEND] Email sent to {to}")
    except Exception as e:
        print(f"❌ [RESEND] Failed to send email to {to}: {e}")