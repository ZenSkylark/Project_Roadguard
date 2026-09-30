from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./roadguard.db"
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    STORAGE_ROOT: str = "./storage"

    # Mail (empty SMTP_HOST = dev mode prints emails to console)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    MAIL_FROM: str = "no-reply@roadguard.ph"

    # Mailtrap (sandbox testing)
    MAILTRAP_USERNAME: str = ""
    MAILTRAP_PASSWORD: str = ""
    MAILTRAP_FROM: str = "noreply@roadguard.ph"

    # Resend (real delivery)
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "noreply@roadguard.ph"

    # OCR engine: stub | paddle | trained
    OCR_BACKEND: str = "stub"
    TRAINED_OCR_PATH: str = "./models/plate_ocr.onnx"

    # SMS provider (empty = dev mode prints SMS to console)
    SMS_PROVIDER: str = ""

    # Twilio (International SMS)
    TWILIO_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Semaphore (Philippine SMS)
    SEMAPHORE_API_KEY: str = ""
    SEMAPHORE_SENDER: str = "ROADGUARD"

    # Evidence retention window in days
    RETENTION_DAYS: int = 30

    model_config = {"env_file": ".env"}


settings = Settings()