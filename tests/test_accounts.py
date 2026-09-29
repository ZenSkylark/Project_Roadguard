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
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def register(c, username="juan_officer", password="Roadguard1",
             email="juan@roadguard.ph", position="officer"):
    return c.post("/api/accounts/register", json={
        "username": username, "email": email,
        "password": password, "position": position
    })


def login(c, username="juan_officer", password="Roadguard1"):
    return c.post("/api/auth/login", data={"username": username, "password": password})


def token_of(c, username="juan_officer", password="Roadguard1"):
    return login(c, username, password).json()["access_token"]


class TestRegister:
    def test_register_success(self, client):
        r = register(client)
        assert r.status_code == 201
        body = r.json()
        assert body["username"] == "juan_officer"
        assert body["position"] == "officer"
        assert re.fullmatch(r"RG-\d{4}-\d{4}", body["uid"])

    def test_auto_uid_generated(self, client):
        r = register(client)
        assert r.status_code == 200 or r.status_code == 201
        assert r.json()["uid"].startswith("RG-")

    def test_weak_password_rejected(self, client):
        r = register(client, password="weak")
        assert r.status_code == 422

    def test_bad_username_rejected(self, client):
        # "admin" is pre-seeded, so attempting to register it returns 409 Conflict
        r = register(client, username="admin")
        assert r.status_code == 409

    def test_invalid_email_format_rejected(self, client):
        # Pydantic rejects invalid email formats with 422
        r = register(client, email="not-an-email")
        assert r.status_code == 422

    def test_self_register_admin_rejected(self, client):
        r = register(client, position="administrator")
        assert r.status_code == 422

    def test_duplicate_username_rejected(self, client):
        register(client)
        r = register(client)
        assert r.status_code == 409


class TestLoginAndRBAC:
    def test_login_success(self, client):
        register(client)
        r = login(client)
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_bad_password(self, client):
        register(client)
        r = login(client, password="WrongPass1")
        assert r.status_code == 401

    def test_me_with_token(self, client):
        register(client)
        t = token_of(client)
        r = client.get("/api/accounts/me", headers=_hdr(t))
        assert r.status_code == 200
        assert r.json()["username"] == "juan_officer"

    def test_me_without_token(self, client):
        r = client.get("/api/accounts/me")
        assert r.status_code == 401

    def test_officer_cannot_list_accounts(self, client):
        register(client)
        t = token_of(client)
        r = client.get("/api/accounts", headers=_hdr(t))
        assert r.status_code == 403

    def test_admin_can_list_accounts(self, client):
        register(client)
        admin_token = login(client, "admin", "Admin123!").json()["access_token"]
        r = client.get("/api/accounts", headers=_hdr(admin_token))
        assert r.status_code == 200
        users = r.json()
        assert any(u["username"] == "juan_officer" for u in users)
        assert any(u["username"] == "admin" for u in users)

    def test_promote_then_disable(self, client):
        register(client, username="viewer1", email="v1@roadguard.ph", position="viewer")
        admin_token = login(client, "admin", "Admin123!").json()["access_token"]
        
        # Find the user's UID via the list endpoint
        users = client.get("/api/accounts", headers=_hdr(admin_token)).json()
        viewer = next(u for u in users if u["username"] == "viewer1")
        uid = viewer["uid"]
        
        # Promote
        r = client.patch(f"/api/accounts/{uid}/position",
                         json={"position": "officer"}, headers=_hdr(admin_token))
        assert r.status_code == 200 and r.json()["position"] == "officer"
        # Disable
        r = client.patch(f"/api/accounts/{uid}/status",
                         json={"is_active": False}, headers=_hdr(admin_token))
        assert r.status_code == 200 and r.json()["is_active"] is False
        # Login should fail now
        assert login(client, "viewer1", "Roadguard1").status_code == 403


class TestLockout:
    def test_lock_after_five_failures(self, client):
        register(client)
        for _ in range(5):
            login(client, password="wrong")
        r = login(client, password="Roadguard1")
        assert r.status_code == 423  # Locked


class TestPasswords:
    def test_change_password(self, client):
        register(client)
        t = token_of(client)
        r = client.post("/api/auth/change-password",
                        json={"old_password": "Roadguard1", "new_password": "NewRoadguard1!"},
                        headers=_hdr(t))
        assert r.status_code == 200
        # Old password fails
        assert login(client).status_code == 401
        # New password works
        assert login(client, password="NewRoadguard1!").status_code == 200

    def test_forgot_and_reset(self, client, monkeypatch):
        sent = {}
        from backend.routers import auth as auth_router
        monkeypatch.setattr(auth_router, "send_mail",
                            lambda to, subj, body: sent.update(body=body))
        register(client)
        r = client.post("/api/auth/forgot-password",
                        json={"email": "juan@roadguard.ph"})
        assert r.status_code == 200
        token = re.search(r"[A-Za-z0-9\-_]{20,}", sent["body"]).group()
        r = client.post("/api/auth/reset-password",
                        json={"token": token, "new_password": "Reset123!"})
        assert r.status_code == 200
        assert login(client, password="Reset123!").status_code == 200

    def test_forgot_unknown_email_does_not_leak(self, client):
        r = client.post("/api/auth/forgot-password",
                        json={"email": "ghost@roadguard.ph"})
        assert r.status_code == 200  # Same generic response


class TestMFA:
    def test_full_sms_mfa_flow(self, client, monkeypatch):
        sent = {}
        from backend.routers import auth as auth_router
        monkeypatch.setattr(auth_router, "send_sms",
                            lambda phone, body: sent.update(body=body))
        register(client)
        t = token_of(client)
        # Setup phone
        r = client.post("/api/auth/mfa/setup",
                        json={"phone_number": "09171234567"}, headers=_hdr(t))
        assert r.status_code == 200
        code = re.search(r"\d{6}", sent["body"]).group()
        # Enable MFA
        assert client.post("/api/auth/mfa/enable", json={"code": code},
                           headers=_hdr(t)).status_code == 200
        # Login now requires MFA
        r = login(client)
        assert r.status_code == 200 and r.json()["mfa_required"] is True
        # Verify MFA (re-sends code)
        code2 = re.search(r"\d{6}", sent["body"]).group()
        v = client.post("/api/auth/mfa/verify",
                        json={"mfa_token": r.json()["mfa_token"], "code": code2})
        assert v.status_code == 200 and "access_token" in v.json()
        # Access protected route
        assert client.get("/api/accounts/me",
                          headers=_hdr(v.json()["access_token"])).status_code == 200

    def test_mfa_wrong_code_rejected(self, client, monkeypatch):
        from backend.routers import auth as auth_router
        monkeypatch.setattr(auth_router, "send_sms", lambda phone, body: None)
        register(client)
        t = token_of(client)
        client.post("/api/auth/mfa/setup",
                    json={"phone_number": "09171234567"}, headers=_hdr(t))
        r = client.post("/api/auth/mfa/enable", json={"code": "000000"}, headers=_hdr(t))
        assert r.status_code == 400

    def test_bad_phone_format_rejected(self, client):
        register(client)
        t = token_of(client)
        r = client.post("/api/auth/mfa/setup",
                        json={"phone_number": "12345"}, headers=_hdr(t))
        assert r.status_code == 422