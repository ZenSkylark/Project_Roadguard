"""Send a test email through the Mailtrap sandbox WITHOUT starting the app.

Uses the SMTP credentials already in .env:
    MAILTRAP_USERNAME / MAILTRAP_PASSWORD / MAILTRAP_FROM

Usage:
    python tools/test_mailtrap_direct.py [to_email]

The message lands in your Mailtrap web inbox (sandbox) — never in a real inbox.
"""
import os
import smtplib
import sys
from email.mime.text import MIMEText

from common import load_env

load_env()

PORT = int(os.environ.get("MAILTRAP_PORT", "2525"))
HOST_CANDIDATES = [
    os.environ.get("MAILTRAP_HOST", ""),
    "sandbox.smtp.mailtrap.io",
    "smtp.mailtrap.io",
]


def main():
    username = os.environ.get("MAILTRAP_USERNAME")
    password = os.environ.get("MAILTRAP_PASSWORD")
    if not username or not password:
        sys.exit("❌ MAILTRAP_USERNAME / MAILTRAP_PASSWORD not set in .env")

    to = sys.argv[1] if len(sys.argv) > 1 else "dev@roadguard.ph"
    sender = os.environ.get("MAILTRAP_FROM", "noreply@roadguard.ph")

    msg = MIMEText("If you can read this, Mailtrap SMTP delivery works.\n\n— Roadguard")
    msg["Subject"] = "Roadguard Mailtrap direct test"
    msg["From"] = f"Roadguard <{sender}>"
    msg["To"] = to

    last_err = None
    for host in [h for h in HOST_CANDIDATES if h]:
        try:
            print(f"Connecting to {host}:{PORT} ...")
            with smtplib.SMTP(host, PORT, timeout=15) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(sender, [to], msg.as_string())
            print(f"✅ Accepted. From {sender} → {to}")
            print("   Open your Mailtrap web inbox to view it.")
            return
        except smtplib.SMTPAuthenticationError:
            sys.exit("❌ Authentication failed — check MAILTRAP_USERNAME / MAILTRAP_PASSWORD")
        except Exception as e:
            last_err = e
            print(f"   {host} failed: {e}")

    sys.exit(f"❌ Mailtrap send failed on all hosts: {last_err}")


if __name__ == "__main__":
    main()