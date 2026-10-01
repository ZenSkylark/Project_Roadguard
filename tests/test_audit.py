import re
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


def _set_retention(c, t, sms, days):
    sms["body"] = ""
    r = c.put("/api/system/retention", json={"days": days}, headers=_hdr(t))
    if r.status_code == 428:
        code = re.search(r"\d{6}", sms["body"]).group()
        r = c.put("/api/system/retention", json={"days": days, "code": code}, headers=_hdr(t))
    return r


def _admin_with_mfa(c, sent):
    t = c.post("/api/auth/login",
               data={"username": "admin", "password": "Admin123!"}).json()["access_token"]
    sent["body"] = ""
    r = c.post("/api/auth/mfa/setup", json={"method": "sms", "phone_number": "09171234567"}, headers=_hdr(t))
    assert r.status_code == 200, f"MFA setup failed: {r.status_code} {r.json()}"
    match = re.search(r"\d{6}", sent.get("body", ""))
    assert match, f"No OTP captured. sent={sent}"
    code = match.group()
    c.post("/api/auth/mfa/enable", json={"code": code}, headers=_hdr(t))
    sent["body"] = ""
    return t


def test_admin_can_read_audit_trail(client, sms):
    t = _admin_with_mfa(client, sms)
    assert _set_retention(client, t, sms, 14).status_code == 200
    logs = client.get("/api/system/audit", headers=_hdr(t)).json()
    assert any("retention" in l["action"] for l in logs)


def test_audit_log_is_admin_only(client):
    client.post("/api/accounts/register", json={
        "username": "juan_officer", "email": "juan@roadguard.ph",
        "password": "Roadguard1", "position": "officer"})
    t = client.post("/api/auth/login",
                    data={"username": "juan_officer", "password": "Roadguard1"}).json()["access_token"]
    assert client.get("/api/system/audit", headers=_hdr(t)).status_code == 403


def test_audit_filters(client, sms):
    t = _admin_with_mfa(client, sms)
    assert _set_retention(client, t, sms, 14).status_code == 200
    assert _set_retention(client, t, sms, 21).status_code == 200
    logs = client.get("/api/system/audit?action=retention", headers=_hdr(t)).json()
    assert all("retention" in l["action"] for l in logs)
    assert len(logs) >= 2