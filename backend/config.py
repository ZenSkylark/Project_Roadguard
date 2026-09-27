from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./roadguard.db"
    SECRET_KEY: str = "change-me-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15      # A2: short-lived access
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7         # A2: long-lived refresh
    REQUIRE_EMAIL_VERIFICATION: bool = False   # A3: flip True in production
    RATE_LIMIT_PER_MINUTE: int = 10          
    SMTP_HOST: str = ""            # empty = dev mode (prints emails to console)
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@roadguard.local"
    STORAGE_ROOT: str = "./storage"
    OCR_BACKEND: str = "stub"        # "stub" for dev | "paddle" for production


settings = Settings()