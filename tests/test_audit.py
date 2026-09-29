import re

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import Base, engine
from backend.main import app
from backend.routers import auth as auth_router
from backend.routers import system as system_router


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
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


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _admin_with_mfa(c, sent):
    t = c.post("/api/auth/login",
               data={"username": "admin", "password": "Admin123!"}).json()["access_token"]
    c.post("/api/auth/mfa/setup", json={"phone_number": "09171234567"}, headers=_hdr(t))
    code = re.search(r"\d{6}", sent["body"]).group()
    c.post("/api/auth/mfa/enable", json={"code": code}, headers=_hdr(t))
    return t


def _set_retention(c, t, sent, days):
    c.post("/api/system/stepup/challenge", json={"purpose": "retention"}, headers=_hdr(t))
    code = re.search(r"\d{6}", sent["body"]).group()
    return c.put("/api/system/retention", json={"days": days, "code": code}, headers=_hdr(t))


def test_admin_can_read_audit_trail(client, sms):
    t = _admin_with_mfa(client, sms)
    assert _set_retention(client, t, sms, 14).status_code == 200
    logs = client.get("/api/system/audit", headers=_hdr(t)).json()
    assert isinstance(logs, list) and len(logs) > 0
    actions = {e["action"] for e in logs}
    assert "retention_changed" in actions
    entry = next(e for e in logs if e["action"] == "retention_changed")
    assert entry["username"] == "admin" and "14 days" in (entry["detail"] or "")


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
    assert len(logs) >= 2 and all("retention" in e["action"] for e in logs)