import requests
from ..config import settings


def _get_sms_mode() -> str:
    """Read the current SMS mode from system settings."""
    try:
        from .templates import load_ui_settings
        return load_ui_settings().get("sms_mode", "dev")
    except Exception:
        return "dev"


def send_sms(phone: str, message: str):
    """Route SMS to DEV console, Twilio, or Semaphore."""
    mode = _get_sms_mode()

    # DEV MODE — print to backend console
    if mode == "dev":
        print("\n" + "=" * 50)
        print(f"📱 [DEV SMS] To: {phone}")
        print(f"📱 [DEV SMS] Body: {message}")
        print("=" * 50 + "\n")
        return

    # TWILIO MODE — international delivery
    if mode == "twilio":
        _send_twilio(phone, message)
        return

    # SEMAPHORE MODE — Philippine delivery
    if mode == "semaphore":
        _send_semaphore(phone, message)
        return

    # Fallback for unknown modes
    print(f"⚠️ Unknown SMS mode: {mode}, falling back to DEV")
    print(f"📱 [DEV SMS] To: {phone}\n📱 [DEV SMS] Body: {message}")


def _send_twilio(phone: str, message: str):
    """Send via Twilio API."""
    if not settings.TWILIO_SID:
        print("❌ [TWILIO] Missing TWILIO_SID in .env")
        return
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone
        )
        print(f"✅ [TWILIO] SMS sent to {phone}")
    except ImportError:
        print("❌ [TWILIO] 'twilio' package not installed. Run: pip install twilio")
    except Exception as e:
        print(f"❌ [TWILIO] Failed to send SMS to {phone}: {e}")


def _send_semaphore(phone: str, message: str):
    """Send via Semaphore API."""
    if not settings.SEMAPHORE_API_KEY:
        print("❌ [SEMAPHORE] Missing SEMAPHORE_API_KEY in .env")
        return
    try:
        r = requests.post(
            "https://api.semaphore.co/api/v4/messages",
            data={
                "apikey": settings.SEMAPHORE_API_KEY,
                "number": phone,
                "message": message,
                "sendername": settings.SEMAPHORE_SENDER
            },
            timeout=10
        )
        if r.status_code == 200:
            print(f"✅ [SEMAPHORE] SMS sent to {phone}")
        else:
            print(f"❌ [SEMAPHORE] Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ [SEMAPHORE] Failed to send SMS to {phone}: {e}")