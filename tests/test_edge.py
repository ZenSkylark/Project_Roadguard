import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import Base, engine
from backend.main import app

from edge.config import EdgeConfig
from edge.camera import StubCamera
from edge.firmware import EdgeFirmware, SAFE, ACK
from edge.spool import Spool
from edge.uplink import EdgeClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "OCR_BACKEND", "stub")
    monkeypatch.setattr(settings, "SECRET_KEY", "super-secret-key-for-jwt-needs-32-chars-minimum")
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _admin(c):
    return c.post("/api/auth/login",
                  data={"username": "admin", "password": "Admin123!"}).json()["access_token"]


def _register_device(c, at, device_id="edge-01"):
    r = c.post("/api/edge/devices", json={"device_id": device_id, "name": "Intersection A"},
               headers=_hdr(at))
    assert r.status_code == 200
    return r.json()["device_key"]


def _edge_hdr(key):
    return {"X-Edge-Key": key}


# ─── Server API tests ────────────────────────────────────────────────────────

def test_register_device_admin_only(client):
    at = _admin(client)
    r = client.post("/api/edge/devices", json={"device_id": "edge-01", "name": "A"},
                    headers=_hdr(at))
    assert r.status_code == 200 and "device_key" in r.json()
    assert client.post("/api/edge/devices", json={"device_id": "edge-01", "name": "A"},
                       headers=_hdr(at)).status_code == 409
    assert client.post("/api/edge/devices", json={"device_id": "x", "name": "X"},
                       headers={}).status_code in (401, 403)


def test_telemetry_updates_last_seen(client):
    at = _admin(client)
    key = _register_device(client, at)
    r = client.post("/api/edge/telemetry",
                    json={"cpu_temp": 51.2, "queue_depth": 0, "camera_ok": True},
                    headers=_edge_hdr(key))
    assert r.status_code == 200
    devs = client.get("/api/edge/devices", headers=_hdr(at)).json()
    assert devs[0]["last_seen"] is not None
    assert devs[0]["camera_ok"] is True
    assert client.post("/api/edge/telemetry", json={},
                       headers=_edge_hdr("bad-key")).status_code == 401


def test_command_lifecycle(client):
    at = _admin(client)
    key = _register_device(client, at)
    r = client.post("/api/edge/devices/edge-01/commands",
                    json={"command": "set_mode", "payload": {"armed": False}},
                    headers=_hdr(at))
    assert r.status_code == 200
    cid = r.json()["id"]

    polled = client.get("/api/edge/commands", headers=_edge_hdr(key)).json()["commands"]
    assert len(polled) == 1 and polled[0]["command"] == "set_mode"
    assert client.get("/api/edge/commands", headers=_edge_hdr(key)).json()["commands"] == []

    ack = client.post(f"/api/edge/commands/{cid}/ack",
                      json={"status": "done", "result": "ok"}, headers=_edge_hdr(key))
    assert ack.status_code == 200

    assert client.post("/api/edge/devices/edge-01/commands",
                       json={"command": "explode"}, headers=_hdr(at)).status_code == 422


def test_edge_evidence_sha256_and_duplicate(client):
    at = _admin(client)
    key = _register_device(client, at)
    img = b"\xff\xd8\xff\xe0edgeframe"
    sha = hashlib.sha256(img).hexdigest()
    data = {"event_id": "evt-edge-1", "violation_type": "illegal_parking",
            "captured_at": "2026-09-26T14:03:00", "confidence": "0.9", "sha256": sha}

    r = client.post("/api/edge/evidence", headers=_edge_hdr(key),
                    files={"file": ("f.jpg", img, "image/jpeg")}, data=data)
    assert r.status_code in (200, 201)

    assert client.post("/api/edge/evidence", headers=_edge_hdr(key),
                       files={"file": ("f.jpg", img, "image/jpeg")}, data=data).status_code == 409

    bad = dict(data, event_id="evt-edge-2", sha256="0" * 64)
    assert client.post("/api/edge/evidence", headers=_edge_hdr(key),
                       files={"file": ("f.jpg", img, "image/jpeg")}, data=bad).status_code == 400


# ─── Firmware unit tests (no server) ─────────────────────────────────────────

class FakeClient:
    def __init__(self, fail_uploads=0, commands=None):
        self.uploads = []
        self.telemetry_sent = []   # ← renamed (was shadowing the method)
        self.acks = []
        self.fail_uploads = fail_uploads
        self.commands = commands or []

    def telemetry(self, payload):
        self.telemetry_sent.append(payload)
        return True

    def poll_commands(self):
        out, self.commands = self.commands, []
        return out

    def ack(self, cid, status="done", result=None):
        self.acks.append((cid, status, result))
        return True

    def upload(self, event, image_bytes):
        if self.fail_uploads > 0:
            self.fail_uploads -= 1
            return False, 503
        self.uploads.append((event, image_bytes))
        return True, 201


def test_firmware_capture_spool_upload(tmp_path):
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool"))
    fw = EdgeFirmware(cfg, camera=StubCamera(script=[True]),
                      client=FakeClient(), spool=Spool(cfg.spool_dir))
    fw.run(steps=1)                      # ← 1 step: capture → spool → upload → ACK
    assert len(fw.client.uploads) == 1
    assert fw.spool.depth() == 0
    assert fw.state == ACK


def test_firmware_offline_spool_retry(tmp_path):
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool"))
    fw = EdgeFirmware(cfg, camera=StubCamera(script=[True]),
                      client=FakeClient(fail_uploads=1), spool=Spool(cfg.spool_dir))
    fw.step()
    assert fw.spool.depth() == 1
    fw.step()
    assert fw.spool.depth() == 0
    assert len(fw.client.uploads) == 1


def test_firmware_camera_fault_safe(tmp_path):
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool"))
    cam = StubCamera(); cam.fail = True
    fw = EdgeFirmware(cfg, camera=cam, client=FakeClient(), spool=Spool(cfg.spool_dir))
    fw.step()
    assert fw.state == SAFE


def test_firmware_command_capture_now(tmp_path):
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool"), armed=False)
    fc = FakeClient(commands=[{"id": 7, "command": "capture_now", "payload": {}, "nonce": "ab"}])
    fw = EdgeFirmware(cfg, camera=StubCamera(), client=fc, spool=Spool(cfg.spool_dir))
    fw.step()
    assert len(fc.uploads) == 1
    assert (7, "done", "ok") in fc.acks


def test_firmware_telemetry_heartbeat(tmp_path):
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool"))
    fc = FakeClient()
    fw = EdgeFirmware(cfg, camera=StubCamera(), client=fc, spool=Spool(cfg.spool_dir))
    fw.run(steps=5)
    assert len(fc.telemetry_sent) == 1   


# ─── End-to-end: firmware → real server ──────────────────────────────────────

def test_end_to_end_edge_to_server(client, tmp_path):
    at = _admin(client)
    key = _register_device(client, at)

    edge_http = TestClient(app)  # firmware talks to the real API in-process
    cfg = EdgeConfig(spool_dir=str(tmp_path / "spool2"), device_key=key)
    fw = EdgeFirmware(cfg, camera=StubCamera(script=[True]),
                      client=EdgeClient(cfg, client=edge_http),
                      spool=Spool(cfg.spool_dir))
    fw.run(steps=5)

    violations = client.get("/api/violations", headers=_hdr(at)).json()
    assert len(violations) == 1
    assert violations[0]["status"] == "pending"

    devs = client.get("/api/edge/devices", headers=_hdr(at)).json()
    assert devs[0]["last_seen"] is not None