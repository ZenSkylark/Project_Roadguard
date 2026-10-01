import re
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import Base, engine
from backend.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
    monkeypatch.setattr(settings, "SECRET_KEY", "super-secret-key-for-jwt-needs-32-chars-minimum")
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def sms(monkeypatch):
    sent = {}
    
    def mock_send_sms(phone, body):
        sent["body"] = body
    
    # String-based patching intercepts the call regardless of import style
    monkeypatch.setattr("backend.services.sms.send_sms", mock_send_sms)
    monkeypatch.setattr("backend.routers.system.send_sms", mock_send_sms, raising=False)
    monkeypatch.setattr("backend.routers.auth.send_sms", mock_send_sms, raising=False)
    
    return sent

def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _admin_token(c):
    r = c.post("/api/auth/login", data={"username": "admin", "password": "Admin123!"})
    return r.json()["access_token"]


def _enable_admin_mfa(c, t, sent):
    sent["body"] = ""
    r = c.post("/api/auth/mfa/setup", json={"method": "sms", "phone_number": "09171234567"}, headers=_hdr(t))
    
    # 🔍 DEBUG: If setup fails, print the exact error so we can see why
    assert r.status_code == 200, f"MFA setup failed: {r.status_code} - {r.json()}"
    
    match = re.search(r"\d{6}", sent["body"])
    assert match, f"No OTP captured in SMS. sent={sent}"
    code = match.group()
    
    r2 = c.post("/api/auth/mfa/enable", json={"code": code}, headers=_hdr(t))
    assert r2.status_code == 200, f"MFA enable failed: {r2.status_code} - {r2.json()}"
    sent["body"] = ""


def _upload_and_age(c, t, event_id, days_old, finalize=True):
    r = c.post("/api/evidence",
               files={"file": ("test.jpg", b"\xff\xd8\xff\xe0fakejpg", "image/jpeg")},
               data={"event_id": event_id, "violation_type": "tailgating",
                     "captured_at": (datetime.utcnow() - timedelta(days=days_old)).isoformat(),
                     "confidence": "0.9"},
               headers=_hdr(t))
    assert r.status_code in (200, 201), f"Upload failed: {r.status_code} {r.json()}"
    vid = r.json()["id"]
    if finalize:
        c.patch(f"/api/violations/{vid}/status", json={"status": "approved"}, headers=_hdr(t))
    return vid

def test_purge_requires_mfa(client, sms):
    t = _admin_token(client)
    _upload_and_age(client, t, "evt-old", 40)
    r = client.post("/api/system/retention/purge", headers=_hdr(t))
    assert r.status_code == 428


def test_purge_with_mfa_code(client, sms):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-old", 40)
    _enable_admin_mfa(client, t, sms)
    r = client.post("/api/system/retention/purge", headers=_hdr(t))
    assert r.status_code == 428
    code = re.search(r"\d{6}", sms["body"]).group()
    r = client.post("/api/system/retention/purge", json={"code": code}, headers=_hdr(t))
    assert r.status_code == 200
    assert client.get(f"/api/violations/{vid}", headers=_hdr(t)).status_code == 404


def test_pending_never_purged(client, sms):
    t = _admin_token(client)
    vid = _upload_and_age(client, t, "evt-pending", 40, finalize=False)
    _enable_admin_mfa(client, t, sms)

    # Call retention endpoint WITHOUT code → triggers 428 + sends OTP
    r = client.post("/api/system/retention/purge", headers=_hdr(t))
    assert r.status_code == 428

    # Now read the OTP that was just sent
    code = re.search(r"\d{6}", sms["body"]).group()

    # Call again WITH code → should succeed
    r = client.post("/api/system/retention/purge", json={"code": code}, headers=_hdr(t))
    assert r.status_code == 200

    # Pending violations should NOT be purged
    assert client.get(f"/api/violations/{vid}", headers=_hdr(t)).status_code == 200


def test_retention_save_requires_mfa(client, sms):
    t = _admin_token(client)
    _enable_admin_mfa(client, t, sms)
    r = client.put("/api/system/retention", json={"days": 14}, headers=_hdr(t))
    assert r.status_code == 428
    code = re.search(r"\d{6}", sms["body"]).group()
    r = client.put("/api/system/retention", json={"days": 14, "code": code}, headers=_hdr(t))
    assert r.status_code == 200


def test_retention_config_bounds(client, sms):
    t = _admin_token(client)
    _enable_admin_mfa(client, t, sms)

    # Trigger the retention endpoint to send OTP
    r = client.put("/api/system/retention", json={"days": 0}, headers=_hdr(t))
    assert r.status_code == 428

    # Read the OTP
    code = re.search(r"\d{6}", sms["body"]).group()

    # Now send with code but invalid days → should get 422
    r = client.put("/api/system/retention", json={"days": 0, "code": code}, headers=_hdr(t))
    assert r.status_code == 422


def test_code_is_purpose_bound(client, sms):
    t = _admin_token(client)
    _upload_and_age(client, t, "evt-old", 40)
    _enable_admin_mfa(client, t, sms)
    r = client.post("/api/system/retention/purge", json={"code": "000000"}, headers=_hdr(t))
    assert r.status_code == 401