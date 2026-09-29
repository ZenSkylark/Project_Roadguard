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
from ..services import ocr as ocr_module
from ..services.retention import purge_old_data
from ..services.templates import load_ui_settings, save_ui_settings, list_templates
from ..services.sms import send_sms

router = APIRouter(prefix="/api/system", tags=["system"])
ALLOWED = ("stub", "paddle", "trained")


class OcrBackendIn(BaseModel):
    backend: str

class RetentionIn(BaseModel):
    days: int = Field(ge=0, le=3650)
    @field_validator("days")
    @classmethod
    def _clamp_zero(cls, v: int) -> int:
        return max(1, v)

class TemplateSettingsIn(BaseModel):
    template_dir: str
    default_template: str | None = None

class PurgeIn(BaseModel):
    code: str | None = None


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


# ---------- Retention ----------
@router.get("/retention")
def get_retention(user=Depends(require_position("administrator", "officer", "viewer"))):
    return {"retention_days": settings.RETENTION_DAYS}

@router.put("/retention")
def set_retention(body: RetentionIn, db: Session = Depends(get_db),
                  user=Depends(require_position("administrator"))):
    settings.RETENTION_DAYS = body.days
    audit(db, user.id, "retention_changed", f"{body.days} days")
    return {"retention_days": settings.RETENTION_DAYS}

@router.post("/purge/challenge")
def purge_challenge(user=Depends(require_position("administrator")),
                    db: Session = Depends(get_db)):
    """Step-up auth: text a one-time code before a destructive purge."""
    if not user.mfa_enabled or not user.phone_number:
        raise HTTPException(400, "Enable MFA with a phone number before purging evidence.")
    code = new_otp()
    user.otp_hash = otp_hash(code)
    user.otp_expires = utcnow() + timedelta(minutes=5)
    db.commit()
    audit(db, user.id, "purge_challenge_issued")
    send_sms(user.phone_number,
             f"Roadguard PURGE confirmation code: {code} (valid 5 minutes)")
    return {"message": "Confirmation code sent to your phone"}

@router.post("/purge")
def run_purge(body: PurgeIn,
              user=Depends(require_position("administrator")),
              db: Session = Depends(get_db)):
    if not user.mfa_enabled:
        raise HTTPException(403, "Enable MFA before purging evidence.")
    if not user.otp_hash or not user.otp_expires or user.otp_expires < utcnow():
        raise HTTPException(401, "Challenge expired - request a new confirmation code.")
    if user.otp_hash != otp_hash(body.code or ""):
        raise HTTPException(401, "Invalid confirmation code.")
    user.otp_hash = user.otp_expires = None
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