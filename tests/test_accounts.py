import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.auth import hash_pw
from backend.models import User
import backend.routers.auth as auth_router          # to intercept dev-mail
from backend.config import settings

# ---------- In-memory test database (real roadguard.db untouched) ----------
engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, autoflush=False)

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 10000)
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    db.add(User(uid="RG-2026-0000", username="admin", email="admin@roadguard.ph",
                hashed_password=hash_pw("Admin123!"), position="administrator"))
    db.commit(); db.close()

    def override():
        db = TestSession()
        try: yield db
        finally: db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)                       # no context => lifespan skipped
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

# ---------- Helpers ----------
def register(client, uid=None, username="juan_officer", email="juan@roadguard.ph",
             password="Roadguard1", position="officer"):
    body = {"username": username, "email": email,
            "password": password, "position": position}
    if uid: body["uid"] = uid
    return client.post("/api/accounts/register", json=body)

def login(client, username, password):
    return client.post("/api/auth/login",
                       data={"username": username, "password": password})

def hdr(token): return {"Authorization": f"Bearer {token}"}

def token_of(client, username="admin", password="Admin123!"):
    return login(client, username, password).json()["access_token"]

# ---------- Registration & Validation ----------
class TestRegister:
    def test_register_success(self, client):
        r = register(client, uid="RG-2026-0001")
        assert r.status_code == 201 and r.json()["uid"] == "RG-2026-0001"

    def test_auto_uid_generated(self, client):
        r = register(client, username="auto_uid")
        assert re.fullmatch(r"RG-\d{4}-\d{4}", r.json()["uid"])

    def test_weak_password_rejected(self, client):
        assert register(client, password="abc").status_code == 422

    def test_bad_username_rejected(self, client):
        assert register(client, username="Juan Officer!").status_code == 422

    def test_reserved_email_tld_rejected(self, client):
        assert register(client, email="juan@roadguard.local").status_code == 422

    def test_self_register_admin_rejected(self, client):
        assert register(client, position="administrator").status_code == 422

    def test_duplicate_username_rejected(self, client):
        register(client)
        assert register(client, email="other@roadguard.ph").status_code == 409

# ---------- Login, RBAC, Account Management ----------
class TestLoginAndRBAC:
    def test_login_success(self, client):
        r = login(client, "admin", "Admin123!")
        assert r.status_code == 200 and "access_token" in r.json()

    def test_login_bad_password(self, client):
        assert login(client, "admin", "wrong").status_code == 401

    def test_me_with_token(self, client):
        r = client.get("/api/accounts/me", headers=hdr(token_of(client)))
        assert r.status_code == 200 and r.json()["username"] == "admin"

    def test_me_without_token(self, client):
        assert client.get("/api/accounts/me").status_code == 401

    def test_officer_cannot_list_accounts(self, client):
        register(client)
        t = token_of(client, "juan_officer", "Roadguard1")
        assert client.get("/api/accounts", headers=hdr(t)).status_code == 403

    def test_admin_can_list_accounts(self, client):
        register(client)
        r = client.get("/api/accounts", headers=hdr(token_of(client)))
        assert r.status_code == 200 and len(r.json()) == 2

    def test_promote_then_disable(self, client):
        register(client, uid="RG-2026-0001")
        at = token_of(client)
        r = client.patch("/api/accounts/RG-2026-0001/position",
                         json={"position": "administrator"}, headers=hdr(at))
        assert r.status_code == 200
        jt = token_of(client, "juan_officer", "Roadguard1")
        assert client.get("/api/accounts", headers=hdr(jt)).status_code == 200
        r = client.patch("/api/accounts/RG-2026-0001/status",
                         json={"is_active": False}, headers=hdr(at))
        assert r.status_code == 200
        assert login(client, "juan_officer", "Roadguard1").status_code == 403

# ---------- Brute-force Lockout ----------
class TestLockout:
    def test_lock_after_five_failures(self, client):
        register(client)
        for _ in range(5):
            assert login(client, "juan_officer", "bad").status_code == 401
        assert login(client, "juan_officer", "Roadguard1").status_code == 423

# ---------- Password Lifecycle ----------
class TestPasswords:
    def test_change_password(self, client):
        register(client)
        t = token_of(client, "juan_officer", "Roadguard1")
        r = client.post("/api/auth/change-password",
                        json={"old_password": "Roadguard1", "new_password": "NewRoad2"},
                        headers=hdr(t))
        assert r.status_code == 200
        assert login(client, "juan_officer", "Roadguard1").status_code == 401
        assert login(client, "juan_officer", "NewRoad2").status_code == 200

    def test_forgot_and_reset(self, client, monkeypatch):
        register(client)
        sent = {}
        monkeypatch.setattr(auth_router, "send_mail",
                            lambda to, subject, body: sent.update(body=body))
        assert client.post("/api/auth/forgot-password",
                           json={"email": "juan@roadguard.ph"}).status_code == 200
        token = sent["body"].strip().splitlines()[-1]
        r = client.post("/api/auth/reset-password",
                        json={"token": token, "new_password": "ResetPass1"})
        assert r.status_code == 200
        assert login(client, "juan_officer", "ResetPass1").status_code == 200

    def test_forgot_unknown_email_does_not_leak(self, client):
        r = client.post("/api/auth/forgot-password",
                        json={"email": "ghost@roadguard.ph"})
        assert r.status_code == 200        # identical response = no account enumeration

# ---------- Multi-Factor Authentication ----------
class TestMFA:
    def test_full_sms_mfa_flow(self, client, monkeypatch):
        sent = {}
        monkeypatch.setattr(auth_router, "send_sms",
                            lambda phone, body: sent.update(body=body))
        register(client)
        t = token_of(client, "juan_officer", "Roadguard1")
        r = client.post("/api/auth/mfa/setup",
                        json={"phone_number": "09171234567"}, headers=hdr(t))
        assert r.status_code == 200
        code = re.search(r"\d{6}", sent["body"]).group()
        assert client.post("/api/auth/mfa/enable", json={"code": code},
                           headers=hdr(t)).status_code == 200
        r = login(client, "juan_officer", "Roadguard1").json()
        assert r["mfa_required"] is True
        code2 = re.search(r"\d{6}", sent["body"]).group()   # login re-sends OTP
        v = client.post("/api/auth/mfa/verify",
                        json={"mfa_token": r["mfa_token"], "code": code2})
        assert v.status_code == 200 and "access_token" in v.json()
        assert client.get("/api/accounts/me",
                          headers=hdr(v.json()["access_token"])).status_code == 200

    def test_mfa_wrong_code_rejected(self, client, monkeypatch):
        monkeypatch.setattr(auth_router, "send_sms", lambda phone, body: None)
        register(client)
        t = token_of(client, "juan_officer", "Roadguard1")
        client.post("/api/auth/mfa/setup",
                    json={"phone_number": "09171234567"}, headers=hdr(t))
        r = client.post("/api/auth/mfa/enable", json={"code": "000000"}, headers=hdr(t))
        assert r.status_code == 400

    def test_bad_phone_format_rejected(self, client):
        register(client)
        t = token_of(client, "juan_officer", "Roadguard1")
        r = client.post("/api/auth/mfa/setup",
                        json={"phone_number": "12345"}, headers=hdr(t))
        assert r.status_code == 422