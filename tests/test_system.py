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


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _admin_token(c):
    r = c.post("/api/auth/login", data={"username": "admin", "password": "Admin123!"})
    return r.json()["access_token"]


class TestEmailMode:
    def test_default_email_mode_is_dev(self, client):
        t = _admin_token(client)
        r = client.get("/api/system/email-mode", headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["email_mode"] == "dev"

    def test_admin_can_switch_to_mailtrap(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/email-mode",
                       json={"email_mode": "mailtrap"}, headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["email_mode"] == "mailtrap"
        # Confirm it persisted
        r2 = client.get("/api/system/email-mode", headers=_hdr(t))
        assert r2.json()["email_mode"] == "mailtrap"

    def test_admin_can_switch_to_resend(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/email-mode",
                       json={"email_mode": "resend"}, headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["email_mode"] == "resend"

    def test_admin_can_switch_back_to_dev(self, client):
        t = _admin_token(client)
        client.put("/api/system/email-mode", json={"email_mode": "resend"}, headers=_hdr(t))
        r = client.put("/api/system/email-mode", json={"email_mode": "dev"}, headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["email_mode"] == "dev"

    def test_invalid_email_mode_rejected(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/email-mode",
                       json={"email_mode": "carrier-pigeon"}, headers=_hdr(t))
        assert r.status_code == 400

    def test_email_mode_requires_auth(self, client):
        r = client.get("/api/system/email-mode")
        assert r.status_code == 401

    def test_dev_mode_email_prints_to_console(self, client, capsys):
        from backend.services.email import send_email
        from backend.services.templates import save_ui_settings

        save_ui_settings({"email_mode": "dev"})
        send_email("test@roadguard.ph", "Test Subject", "Your code is 123456")

        captured = capsys.readouterr()
        assert "[DEV EMAIL]" in captured.out
        assert "test@roadguard.ph" in captured.out
        assert "123456" in captured.out

class TestSmsMode:
    def test_default_sms_mode_is_dev(self, client):
        t = _admin_token(client)
        r = client.get("/api/system/sms-mode", headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["sms_mode"] == "dev"

    def test_admin_can_switch_to_twilio(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/sms-mode",
                       json={"sms_mode": "twilio"}, headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["sms_mode"] == "twilio"

    def test_admin_can_switch_to_semaphore(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/sms-mode",
                       json={"sms_mode": "semaphore"}, headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["sms_mode"] == "semaphore"

    def test_invalid_sms_mode_rejected(self, client):
        t = _admin_token(client)
        r = client.put("/api/system/sms-mode",
                       json={"sms_mode": "telepathy"}, headers=_hdr(t))
        assert r.status_code == 400

    def test_dev_mode_sms_prints_to_console(self, client, capsys):
        from backend.services.sms import send_sms
        from backend.services.templates import save_ui_settings

        save_ui_settings({"sms_mode": "dev"})
        send_sms("09171234567", "Your OTP is 654321")

        captured = capsys.readouterr()
        assert "[DEV SMS]" in captured.out
        assert "09171234567" in captured.out
        assert "654321" in captured.out