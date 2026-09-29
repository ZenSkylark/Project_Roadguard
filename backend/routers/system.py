from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth import require_position
from ..config import settings
from ..database import get_db
from ..services import ocr as ocr_module
from ..services.retention import purge_old_data

router = APIRouter(prefix="/api/system", tags=["system"])
ALLOWED = ("stub", "paddle", "trained")


class OcrBackendIn(BaseModel):
    backend: str


class RetentionIn(BaseModel):
    days: int = Field(ge=0, le=3650)

    @field_validator("days")
    @classmethod
    def _clamp_zero(cls, v: int) -> int:
        """0 is auto-corrected to 1 — retention can never mean
        'destroy everything instantly'."""
        return max(1, v)


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


@router.get("/retention")
def get_retention(user=Depends(require_position("administrator", "officer", "viewer"))):
    return {"retention_days": settings.RETENTION_DAYS}


@router.put("/retention")
def set_retention(body: RetentionIn, db: Session = Depends(get_db),
                  user=Depends(require_position("administrator"))):
    settings.RETENTION_DAYS = body.days
    audit(db, user.id, "retention_changed", f"{body.days} days")
    return {"retention_days": settings.RETENTION_DAYS}


@router.post("/purge")
def run_purge(db: Session = Depends(get_db),
              user=Depends(require_position("administrator"))):
    return purge_old_data(db, settings.RETENTION_DAYS, actor_id=user.id)