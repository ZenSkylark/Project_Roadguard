from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_number = Column(String, nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    hashed_password = Column(String, nullable=False)
    position = Column(String, default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_method = Column(String, nullable=True)
    otp_hash = Column(String, nullable=True)
    otp_expires = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    reset_hash = Column(String, nullable=True)
    reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Violation(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    uid = Column(String, index=True, nullable=False)
    plate_number = Column(String, nullable=True)
    plate_text = Column(String, nullable=True)
    plate_source = Column(String, nullable=True)
    plate_confidence = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    violation_type = Column(String, nullable=False)
    location = Column(String, nullable=True)
    captured_at = Column(DateTime, nullable=False)
    status = Column(String, default="pending", nullable=False)
    evidence_path = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    report_path = Column(String, nullable=True)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by = Column(String, nullable=True)
    rejected_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EdgeDevice(Base):
    __tablename__ = "edge_devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    firmware_version = Column(String, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    cpu_temp = Column(Float, nullable=True)
    cpu_load = Column(Float, nullable=True)
    disk_free = Column(Float, nullable=True)
    queue_depth = Column(Integer, nullable=True)
    camera_ok = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EdgeCommand(Base):
    __tablename__ = "edge_commands"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    command = Column(String, nullable=False)
    payload = Column(String, nullable=True)
    nonce = Column(String, unique=True, nullable=False)
    status = Column(String, default="pending", nullable=False)
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acked_at = Column(DateTime, nullable=True)