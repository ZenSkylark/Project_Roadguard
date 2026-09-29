from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from pathlib import Path

from ..audit import audit
from ..auth import require_position, new_otp, otp_hash
from ..clock import utcnow
from ..config import settings
from ..database import get_db
from ..models import AuditLog, User
from ..services import ocr as ocr_module
from ..services.retention import purge_old_data
from ..services.templates import load_ui_settings, save_ui_settings, list_templates
from ..services.sms import send_sms

router = APIRouter(prefix="/api/system", tags=["system"])
ALLOWED = ("stub", "paddle", "trained")

PURPOSE_MESSAGES = {
    "purge": "Roadguard PURGE confirmation code: {code} (valid 5 minutes)",
    "retention": "Roadguard RETENTION CHANGE confirmation code: {code} (valid 5 minutes)",
}


class OcrBackendIn(BaseModel):
    backend: str

class RetentionIn(BaseModel):
    days: int = Field(ge=0, le=3650)
    code: str | None = None

    @field_validator("days")
    @classmethod
    def _clamp_zero(cls, v: int) -> int:
        return max(1, v)

class TemplateSettingsIn(BaseModel):
    template_dir: str
    default_template: str | None = None

class PurgeIn(BaseModel):
    code: str | None = None

class StepUpChallengeIn(BaseModel):
    purpose: str = Field(pattern="^(purge|retention)$")


def _verify_stepup(user, code: str | None, purpose: str):
    """Verify a purpose-bound one-time code; clears it on success."""
    if not user.mfa_enabled:
        raise HTTPException(403, "Enable MFA before this action.")
    if not user.otp_hash or not user.otp_expires or user.otp_expires < utcnow():
        raise HTTPException(401, "Challenge expired - request a new confirmation code.")
    if user.otp_hash != otp_hash(f"{code or ''}:{purpose}"):
        raise HTTPException(401, "Invalid confirmation code.")
    user.otp_hash = user.otp_expires = None


# ---------- OCR ----------
@router.get("/ocr")
def get_ocr_backend(user=Depends(require_position("administrator", "officer", "viewer"))):
    return {"backend": settings.OCR_BACKEND, "options": list(ALLOWED)}

@router.put("/ocr")
def set_ocr_backend(body: OcrBackendIn, db: Session = Depends(get_db),
                    user=Depends(require_position("administrator"))):
    if body.backend not in ALLOWED:
        raise HTTPException(400, f"backend must be one of {ALLOWED}")
    settings.OCR_BACKEND = body.backend
    ocr_module.reset_ocr_cache()
    audit(db, user.id, "ocr_backend_changed", body.backend)
    return {"backend": settings.OCR_BACKEND}


# ---------- Step-up MFA challenges ----------
@router.post("/stepup/challenge")
def stepup_challenge(body: StepUpChallengeIn,
                     user=Depends(require_position("administrator")),
                     db: Session = Depends(get_db)):
    """Text a purpose-bound one-time code before a critical action."""
    if not user.mfa_enabled or not user.phone_number:
        raise HTTPException(400, "Enable MFA with a phone number before this action.")
    code = new_otp()
    user.otp_hash = otp_hash(f"{code}:{body.purpose}")
    user.otp_expires = utcnow() + timedelta(minutes=5)
    db.commit()
    audit(db, user.id, "stepup_challenge_issued", body.purpose)
    send_sms(user.phone_number, PURPOSE_MESSAGES[body.purpose].format(code=code))
    return {"message": "Confirmation code sent to your phone"}


# ---------- Retention ----------
@router.get("/retention")
def get_retention(user=Depends(require_position("administrator", "officer", "viewer"))):
    return {"retention_days": settings.RETENTION_DAYS}

@router.put("/retention")
def set_retention(body: RetentionIn, db: Session = Depends(get_db),
                  user=Depends(require_position("administrator"))):
    _verify_stepup(user, body.code, "retention")
    settings.RETENTION_DAYS = body.days
    audit(db, user.id, "retention_changed", f"{body.days} days")
    return {"retention_days": settings.RETENTION_DAYS}

@router.post("/purge")
def run_purge(body: PurgeIn,
              user=Depends(require_position("administrator")),
              db: Session = Depends(get_db)):
    _verify_stepup(user, body.code, "purge")
    return purge_old_data(db, settings.RETENTION_DAYS, actor_id=user.id)


# ---------- Templates ----------
@router.get("/templates")
def get_templates(user=Depends(require_position("administrator", "officer", "viewer"))):
    s = load_ui_settings()
    return {
        "template_dir": s.get("template_dir", "./templates"),
        "default_template": s.get("default_template"),
        "available": list_templates(),
    }

@router.put("/templates/settings")
def set_template_settings(body: TemplateSettingsIn, db: Session = Depends(get_db),
                          user=Depends(require_position("administrator"))):
    p = Path(body.template_dir)
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            raise HTTPException(400, f"Directory does not exist and could not be created: {body.template_dir}")
    data = {"template_dir": body.template_dir, "default_template": body.default_template}
    save_ui_settings(data)
    audit(db, user.id, "template_settings_changed",
          f"dir={body.template_dir}, default={body.default_template}")
    return data


# ---------- Audit Trail ----------
@router.get("/audit")
def get_audit_logs(action: str | None = None, username: str | None = None,
                    limit: int = 100,
                    user=Depends(require_position("administrator")),
                    db: Session = Depends(get_db)):
    """Admin-only forensic view of every audited event, newest first."""
    limit = max(1, min(limit, 1000))
    q = (db.query(AuditLog, User.username)
         .join(User, AuditLog.user_id == User.id, isouter=True))
    if action:
        q = q.filter(AuditLog.action.contains(action))
    if username:
        q = q.filter(User.username.contains(username))
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{
        "id": a.id,
        "at": a.created_at,
        "username": uname or "system",
        "action": a.action,
        "detail": a.detail,
        "ip": a.ip,
    } for a, uname in rows]