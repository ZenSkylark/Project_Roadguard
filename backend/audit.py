from datetime import datetime
from sqlalchemy.orm import Session
from .models import AuditLog


def audit(db: Session, user_id: int, action: str, detail: str = None, ip: str = None) -> None:
    """Write an entry to the immutable audit log."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip=ip,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()