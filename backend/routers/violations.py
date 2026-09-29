import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import require_position
from ..database import get_db
from ..models import Violation
from ..schemas import PlateIn
from ..services.report import generate_report

router = APIRouter(prefix="/api/violations", tags=["violations"])
ANY = ("administrator", "officer", "viewer")

def _get(db: Session, vid: int) -> Violation:
    v = db.get(Violation, vid)
    if not v or v.status == "deleted":
        raise HTTPException(404, "Violation not found")
    return v

@router.get("")
def list_violations(status: str | None = None, db: Session = Depends(get_db),
                    user=Depends(require_position(*ANY))):
    q = db.query(Violation)
    if status:
        q = q.filter(Violation.status == status)
    else:
        q = q.filter(Violation.status != "deleted")
    return [{"id": v.id, "event_id": v.event_id, "violation_type": v.violation_type,
             "confidence": v.confidence, "captured_at": v.captured_at,
             "plate_text": v.plate_text, "plate_source": v.plate_source,
             "status": v.status}
            for v in q.order_by(Violation.id.desc()).all()]

@router.patch("/{vid}/plate")
def manual_plate(vid: int, body: PlateIn, db: Session = Depends(get_db),
                 user=Depends(require_position("officer", "administrator"))):
    v = _get(db, vid)
    v.plate_text = body.plate_text
    v.plate_source = "manual"
    v.report_path = generate_report(v)
    db.commit()
    audit(db, user.id, "plate_manual_set", f"violation={vid} plate={v.plate_text}")
    return {"id": v.id, "plate_text": v.plate_text, "plate_source": "manual"}

@router.post("/{vid}/finalize")
def finalize(vid: int, db: Session = Depends(get_db),
             user=Depends(require_position("officer", "administrator"))):
    v = _get(db, vid)
    if not v.plate_text:
        raise HTTPException(400, "Plate must be filled (OCR or manual) before finalizing")
    v.status = "finalized"
    v.report_path = generate_report(v)
    db.commit()
    audit(db, user.id, "violation_finalized", f"violation={vid}")
    return {"id": v.id, "status": v.status}

@router.post("/{vid}/reject")
def reject(vid: int, db: Session = Depends(get_db),
           user=Depends(require_position("administrator"))):   # evidence destruction = admin only
    v = _get(db, vid)
    for p in (v.image_path, v.report_path):
        if p and os.path.exists(p):
            os.remove(p)
    v.status = "deleted"
    db.commit()
    audit(db, user.id, "evidence_deleted", f"violation={vid}")
    return {"id": v.id, "status": v.status}

@router.get("/{vid}/report")
def download_report(vid: int, db: Session = Depends(get_db),
                    user=Depends(require_position(*ANY))):
    v = _get(db, vid)
    if not v.report_path or not os.path.exists(v.report_path):
        raise HTTPException(404, "Report not found")
    return FileResponse(v.report_path, filename=f"report_{v.id}.docx")

@router.get("/{vid}/image")
def download_image(vid: int, db: Session = Depends(get_db),
                   user=Depends(require_position(*ANY))):
    v = _get(db, vid)
    if not v.image_path or not os.path.exists(v.image_path):
        raise HTTPException(404, "Image not found")
    return FileResponse(v.image_path, filename=f"evidence_{v.id}.jpg")