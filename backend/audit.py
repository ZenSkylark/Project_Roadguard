from sqlalchemy.orm import Session
from .models import AuditLog

def audit(db: Session, user_id: int | None, action: str,
          detail: str | None = None, ip: str | None = None):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail, ip=ip))
    db.commit()