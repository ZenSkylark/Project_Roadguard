from datetime import timedelta
import re

import pytest
from fastapi.testclient import TestClient

from backend.clock import utcnow
from backend.config import settings
from backend.database import Base, SessionLocal, engine
from backend.main import app
from backend.models import Violation
from backend.routers import auth as auth_router
from backend.routers import system as system_router


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
    monkeypatch.setattr(settings, "SECRET_KEY", "super-secret-key-for-jwt-needs-32-chars-minimum")  # ADD THIS
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def sms(monkeypatch):
    sent = {}
    monkeypatch.setattr(auth_router, "send_sms", lambda p, b: sent.update(body=b))
    monkeypatch.setattr(system_router, "send_sms", lambda p, b: sent.update(body=b))
    return sent


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


def _enable_admin_mfa(c, t, sent):
    c.post("/api/auth/mfa/setup", json={"method": "sms", "phone_number": "09171234567"}, headers=_hdr(t))
    code = re.search(r"\d{6}", sent["body"]).group()
    c.post("/api/auth/mfa/enable", json={"code": code}, headers=_hdr(t))


def _stepup_code(c, t, sent, purpose):
    r = c.post("/api/system/stepup/challenge", json={"purpose": purpose}, headers=_hdr(t))
    assert r.status_code == 200
    return re.search(r"\d{6}", sent["body"]).group()


def test_purge_requires_mfa(client, sms):
    t = _admin_token(client)
    _upload_and_age(client, t, "evt-old", 40)
    r = client.post("/api/system/purge", json={"code": "123456"}, headers=_hdr(t))
    assert r.status_code == 403


def test_purge_with_mfa_code(client, sms):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-old", 40)
    _enable_admin_mfa(client, t, sms)
    code = _stepup_code(client, t, sms, "purge")
    r = client.post("/api/system/purge", json={"code": code}, headers=_hdr(t))
    assert r.status_code == 200 and r.json()["violations_deleted"] == 1
    lst = client.get("/api/violations", headers=_hdr(t)).json()
    assert all(v["id"] != vid for v in lst)


def test_pending_never_purged(client, sms):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-pending", 40, finalize=False)
    _enable_admin_mfa(client, t, sms)
    code = _stepup_code(client, t, sms, "purge")
    client.post("/api/system/purge", json={"code": code}, headers=_hdr(t))
    lst = client.get("/api/violations", headers=_hdr(t)).json()
    assert any(v["id"] == vid for v in lst)


def test_retention_save_requires_mfa(client, sms):
    t = _admin_token(client)
    r = client.put("/api/system/retention", json={"days": 7, "code": "123456"}, headers=_hdr(t))
    assert r.status_code == 403


def test_retention_config_bounds(client, sms):
    t = _admin_token(client)
    _enable_admin_mfa(client, t, sms)

    def put_days(days):
        code = _stepup_code(client, t, sms, "retention")
        return client.put("/api/system/retention", json={"days": days, "code": code}, headers=_hdr(t))

    assert put_days(7).status_code == 200
    assert client.get("/api/system/retention", headers=_hdr(t)).json()["retention_days"] == 7
    r = put_days(0)
    assert r.status_code == 200 and r.json()["retention_days"] == 1
    assert put_days(-5).status_code == 422
    assert put_days(99999).status_code == 422


def test_code_is_purpose_bound(client, sms):
    t = _admin_token(client)
    _upload_and_age(client, t, "evt-old", 40)
    _enable_admin_mfa(client, t, sms)
    code = _stepup_code(client, t, sms, "retention")   # issued for retention
    r = client.post("/api/system/purge", json={"code": code}, headers=_hdr(t))
    assert r.status_code == 401                          # cannot be replayed on purge