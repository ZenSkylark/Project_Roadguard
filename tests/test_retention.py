from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.clock import utcnow
from backend.config import settings
from backend.database import Base, SessionLocal, engine
from backend.main import app
from backend.models import Violation


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _admin_token(c):
    r = c.post("/api/auth/login", data={"username": "admin", "password": "Admin123!"})
    return r.json()["access_token"]


def _upload_and_age(c, token, event, days_old, finalize=True):
    r = c.post("/api/evidence",
               files={"file": (f"{event}_plate_evidence.jpg", b"\xff\xd8\xff", "image/jpeg")},
               data={"event_id": event, "violation_type": "tailgating",
                     "confidence": "0.9", "captured_at": utcnow().isoformat()},
               headers=_hdr(token))
    vid = r.json()["id"]
    if finalize:
        c.post(f"/api/violations/{vid}/finalize", headers=_hdr(token))
    db = SessionLocal()
    v = db.get(Violation, vid)
    v.captured_at = utcnow() - timedelta(days=days_old)
    db.commit()
    db.close()
    return vid


def test_purge_removes_old_finalized(client):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-old", 40)
    r = client.post("/api/system/purge", headers=_hdr(t))
    assert r.status_code == 200 and r.json()["violations_deleted"] == 1
    lst = client.get("/api/violations", headers=_hdr(t)).json()
    assert all(v["id"] != vid for v in lst)


def test_pending_never_purged(client):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-pending", 40, finalize=False)
    client.post("/api/system/purge", headers=_hdr(t))
    lst = client.get("/api/violations", headers=_hdr(t)).json()
    assert any(v["id"] == vid for v in lst)


def test_retention_config_bounds(client):
    t = _admin_token(client)
    h = _hdr(t)
    assert client.put("/api/system/retention", json={"days": 7}, headers=h).status_code == 200
    assert client.get("/api/system/retention", headers=h).json()["retention_days"] == 7
    # 0 is auto-clamped to 1 (never "delete everything instantly")
    r = client.put("/api/system/retention", json={"days": 0}, headers=h)
    assert r.status_code == 200 and r.json()["retention_days"] == 1
    # negatives and absurd values are still rejected
    assert client.put("/api/system/retention", json={"days": -5}, headers=h).status_code == 422
    assert client.put("/api/system/retention", json={"days": 99999}, headers=h).status_code == 422