import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.auth import hash_pw
from backend.models import User

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, autoflush=False)

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
    monkeypatch.setattr(settings, "SECRET_KEY", "super-secret-key-for-jwt-needs-32-chars-minimum")  # ADD THIS
    Base.metadata.create_all(bind=engine)
    import backend.ratelimit as rl
    rl._hits.clear()
    db = TestSession()
    db.add_all([
        User(uid="RG-2026-0000", username="admin", email="admin@roadguard.ph",
             hashed_password=hash_pw("Admin123!"), position="administrator", email_verified=True),
        User(uid="RG-2026-0001", username="officer", email="officer@roadguard.ph",
             hashed_password=hash_pw("Officer123!"), position="officer", email_verified=True),
        User(uid="RG-2026-0002", username="viewer", email="viewer@roadguard.ph",
             hashed_password=hash_pw("Viewer123!"), position="viewer", email_verified=True),
    ])
    db.commit(); db.close()

    def override():
        db = TestSession()
        try: yield db
        finally: db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def tok(client, u, p):
    r = client.post("/api/auth/login", data={"username": u, "password": p})
    assert r.status_code == 200, f"Login failed for {u}: {r.status_code} {r.json()}"
    return r.json()["access_token"]

def hdr(t): return {"Authorization": f"Bearer {t}"}

def upload(client, token, name="plate_evidence.jpg", event_id="evt-001"):
    return client.post("/api/evidence", headers=hdr(token),
                       files={"file": (name, PNG_1x1, "image/jpeg")},
                       data={"event_id": event_id, "violation_type": "illegal_parking",
                             "confidence": "0.87", "captured_at": "2026-09-26T14:03:00"})

class TestUpload:
    def test_upload_readable_plate(self, client):
        r = upload(client, tok(client, "officer", "Officer123!"))
        assert r.status_code == 201
        body = r.json()
        assert body["plate"] == "ABC1234" and body["directory"] == "readable"
        assert (Path(settings.STORAGE_ROOT) / "readable" / (body["event_id"] + "_plate_evidence.jpg")).exists()

    def test_upload_unreadable_plate(self, client):
        r = upload(client, tok(client, "officer", "Officer123!"), name="blurry.jpg")
        body = r.json()
        assert r.status_code == 201 and body["plate"] is None and body["directory"] == "unreadable"

    def test_duplicate_event_rejected(self, client):
        t = tok(client, "officer", "Officer123!")
        upload(client, t)
        assert upload(client, t).status_code == 409

    def test_upload_requires_auth(self, client):
        assert upload(client, "no-token").status_code == 401

    def test_viewer_cannot_upload(self, client):
        assert upload(client, tok(client, "viewer", "Viewer123!")).status_code == 403

class TestWorkflow:
    def test_manual_plate_then_finalize(self, client):
        t = tok(client, "officer", "Officer123!")
        vid = upload(client, t, name="blurry.jpg").json()["id"]
        assert client.post(f"/api/violations/{vid}/finalize", headers=hdr(t)).status_code == 400
        r = client.patch(f"/api/violations/{vid}/plate",
                         json={"plate_text": "abc 1234"}, headers=hdr(t))
        assert r.status_code == 200 and r.json()["plate_text"] == "ABC1234"
        r = client.post(f"/api/violations/{vid}/finalize", headers=hdr(t))
        assert r.status_code == 200 and r.json()["status"] == "finalized"

    def test_bad_plate_format_rejected(self, client):
        t = tok(client, "officer", "Officer123!")
        vid = upload(client, t, name="blurry.jpg").json()["id"]
        r = client.patch(f"/api/violations/{vid}/plate",
                         json={"plate_text": "hello!"}, headers=hdr(t))
        assert r.status_code == 422

    def test_viewer_cannot_finalize(self, client):
        ot = tok(client, "officer", "Officer123!")
        vid = upload(client, ot).json()["id"]
        r = client.post(f"/api/violations/{vid}/finalize",
                        headers=hdr(tok(client, "viewer", "Viewer123!")))
        assert r.status_code == 403

    def test_reject_is_admin_only_and_deletes_files(self, client):
        ot = tok(client, "officer", "Officer123!")
        at = tok(client, "admin", "Admin123!")
        vid = upload(client, ot, name="blurry.jpg").json()["id"]
        assert client.post(f"/api/violations/{vid}/reject", headers=hdr(ot)).status_code == 403
        r = client.post(f"/api/violations/{vid}/reject", headers=hdr(at))
        assert r.status_code == 200 and r.json()["status"] == "deleted"
        assert client.get(f"/api/violations/{vid}/image", headers=hdr(at)).status_code == 404

    def test_list_and_downloads_for_viewer(self, client):
        ot = tok(client, "officer", "Officer123!")
        vt = tok(client, "viewer", "Viewer123!")
        vid = upload(client, ot).json()["id"]
        r = client.get("/api/violations", headers=hdr(vt))
        assert r.status_code == 200 and len(r.json()) == 1
        assert client.get(f"/api/violations/{vid}/report", headers=hdr(vt)).status_code == 200
        assert client.get(f"/api/violations/{vid}/image", headers=hdr(vt)).status_code == 200

    