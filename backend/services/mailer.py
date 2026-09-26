import smtplib
from email.mime.text import MIMEText
from ..config import settings

def send_mail(to: str, subject: str, body: str):
    if not settings.SMTP_HOST:                       # DEV: print to uvicorn console
        print(f"\n[DEV MAIL] to={to} | {subject}\n{body}\n")
        return
    msg = MIMEText(body); msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM; msg["To"] = to
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
        s.starttls(); s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.send_message(msg)