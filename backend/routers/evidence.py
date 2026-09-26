from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import require_position
from ..config import settings
from ..database import get_db
from ..models import Violation
from ..services.ocr import get_ocr
from ..services.report import generate_report
from ..ws import manager

router = APIRouter(prefix="/api", tags=["evidence"])

@router.post("/evidence", status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    event_id: str = Form(...),
    violation_type: str = Form(...),
    confidence: float = Form(...),
    captured_at: datetime = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_position("officer", "administrator")),
):
    if db.query(Violation).filter(Violation.event_id == event_id).first():
        raise HTTPException(409, "Event already uploaded")

    inbox = Path(settings.STORAGE_ROOT) / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    tmp = inbox / f"{event_id}_{file.filename}"
    tmp.write_bytes(await file.read())

    # Flowchart: "Is the License Plate Readable?"
    plate = get_ocr().read_plate(str(tmp))
    subdir = "readable" if plate else "unreadable"
    final = Path(settings.STORAGE_ROOT) / subdir / tmp.name
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp.rename(final)

    v = Violation(event_id=event_id, violation_type=violation_type,
                  confidence=confidence, captured_at=captured_at,
                  image_path=str(final), uploaded_by=user.id,
                  plate_text=plate.text if plate else None,
                  plate_confidence=plate.confidence if plate else None,
                  plate_source="ocr" if plate else None, status="pending")
    db.add(v); db.commit(); db.refresh(v)
    v.report_path = generate_report(v)
    db.commit()
    audit(db, user.id, "evidence_uploaded", f"event={event_id} dir={subdir}")
    await manager.broadcast({"type": "new_violation", "id": v.id,
                             "event_id": v.event_id,
                             "violation_type": v.violation_type,
                             "plate": v.plate_text, "status": v.status})
    return {"id": v.id, "event_id": v.event_id, "plate": v.plate_text,
            "directory": subdir, "status": v.status}