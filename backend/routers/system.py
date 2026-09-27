from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import require_position
from ..config import settings
from ..database import get_db
from ..services import ocr as ocr_module

router = APIRouter(prefix="/api/system", tags=["system"])
ALLOWED = ("stub", "paddle", "trained")

class OcrBackendIn(BaseModel):
    backend: str

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