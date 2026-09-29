import time
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from ..audit import audit
from ..clock import utcnow
from ..config import settings
from ..models import Violation


def purge_old_data(db: Session, days: int, actor_id: int | None = None) -> dict:
    """Delete finalized violations older than `days`, their files,
    and orphaned inbox uploads. Pending cases are NEVER auto-purged."""
    cutoff = utcnow() - timedelta(days=days)
    root = Path(settings.STORAGE_ROOT)

    old = db.query(Violation).filter(
        Violation.status == "finalized",
        Violation.captured_at < cutoff,
    ).all()

    files_deleted = 0
    for v in old:
        for p in (v.image_path, str(root / "reports" / f"report_{v.id}.docx")):
            if p and Path(p).exists():
                Path(p).unlink()
                files_deleted += 1
        db.delete(v)
    db.commit()

    # Orphan sweep: inbox files older than the window (failed uploads)
    now_ts = time.time()
    inbox = root / "inbox"
    if inbox.exists():
        for fp in inbox.glob("*"):
            if fp.is_file() and (now_ts - fp.stat().st_mtime) > days * 86400:
                fp.unlink()
                files_deleted += 1

    if actor_id:
        audit(db, actor_id, "retention_purge",
              f"violations={len(old)} files={files_deleted}")
    return {"violations_deleted": len(old), "files_deleted": files_deleted}