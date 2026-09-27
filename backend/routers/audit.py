from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import require_position
from ..database import get_db
from ..models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def list_audit(user_id: int | None = None, action: str | None = None,
               limit: int = 100, db: Session = Depends(get_db),
               _=Depends(require_position("administrator"))):
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    rows = q.order_by(AuditLog.id.desc()).limit(limit).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action,
             "detail": r.detail, "ip": r.ip, "created_at": r.created_at}
            for r in rows]