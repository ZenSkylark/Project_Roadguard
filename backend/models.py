from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from .database import Base
from .clock import utcnow

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Boolean, default=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    position = Column(String, default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_method = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    otp_hash = Column(String, nullable=True)
    otp_expires = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    reset_hash = Column(String, nullable=True)
    reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token_hash = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String)
    detail = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class Violation(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, index=True)
    violation_type = Column(String)
    confidence = Column(Float)
    captured_at = Column(DateTime)
    image_path = Column(String)
    uploaded_by = Column(Integer, ForeignKey("users.id"))   # chain of custody
    plate_text = Column(String, nullable=True)
    plate_confidence = Column(Float, nullable=True)
    plate_source = Column(String, nullable=True)            # "ocr" | "manual"
    status = Column(String, default="pending")              # pending|finalized|deleted
    report_path = Column(String, nullable=True)