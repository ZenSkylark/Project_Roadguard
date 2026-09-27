from ..config import settings

def send_sms(phone: str, body: str):
    """Provider-abstracted SMS. Dev mode prints to console;
    production plugs in Semaphore/Twilio via settings.SMS_PROVIDER."""
    if not settings.SMS_PROVIDER:
        print(f"\n[DEV SMS] to={phone}\n{body}\n")
        return
    raise NotImplementedError(
        f"SMS provider '{settings.SMS_PROVIDER}' not integrated yet")