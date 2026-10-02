import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth import require_position
from ..clock import utcnow
from ..config import settings
from ..database import get_db
from ..models import EdgeDevice, EdgeCommand, Violation

router = APIRouter(prefix="/api/edge", tags=["edge"])

ALLOWED_COMMANDS = ("capture_now", "set_config", "set_mode", "reboot", "update_firmware")


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_edge_device(request: Request, db: Session = Depends(get_db)) -> EdgeDevice:
    key = request.headers.get("X-Edge-Key")
    if not key:
        raise HTTPException(401, "Missing edge key")
    dev = db.query(EdgeDevice).filter(EdgeDevice.key_hash == _key_hash(key)).first()
    if not dev or not dev.is_active:
        raise HTTPException(401, "Invalid or disabled edge key")
    return dev


class DeviceRegisterIn(BaseModel):
    device_id: str
    name: str


class CommandIn(BaseModel):
    command: str
    payload: dict | None = None


class TelemetryIn(BaseModel):
    firmware_version: str | None = None
    cpu_temp: float | None = None
    cpu_load: float | None = None
    disk_free: float | None = None
    queue_depth: int | None = None
    camera_ok: bool | None = None


class AckIn(BaseModel):
    status: str = "done"
    result: str | None = None


@router.post("/devices")
def register_device(body: DeviceRegisterIn, db: Session = Depends(get_db),
                    user=Depends(require_position("administrator"))):
    if db.query(EdgeDevice).filter(EdgeDevice.device_id == body.device_id).first():
        raise HTTPException(409, "Device already registered")
    key = secrets.token_urlsafe(32)
    dev = EdgeDevice(device_id=body.device_id, name=body.name, key_hash=_key_hash(key))
    db.add(dev)
    db.commit()
    audit(db, user.id, "edge_device_registered", f"device={body.device_id}")
    return {"device_id": dev.device_id, "device_key": key}


@router.get("/devices")
def list_devices(db: Session = Depends(get_db),
                 user=Depends(require_position("administrator"))):
    devs = db.query(EdgeDevice).order_by(EdgeDevice.id).all()
    return [{"device_id": d.device_id, "name": d.name, "is_active": d.is_active,
             "last_seen": d.last_seen, "firmware_version": d.firmware_version,
             "camera_ok": d.camera_ok, "queue_depth": d.queue_depth} for d in devs]


@router.post("/telemetry")
def telemetry(body: TelemetryIn, db: Session = Depends(get_db),
              device: EdgeDevice = Depends(get_edge_device)):
    device.last_seen = utcnow()
    if body.firmware_version is not None: device.firmware_version = body.firmware_version
    if body.cpu_temp is not None: device.cpu_temp = body.cpu_temp
    if body.cpu_load is not None: device.cpu_load = body.cpu_load
    if body.disk_free is not None: device.disk_free = body.disk_free
    if body.queue_depth is not None: device.queue_depth = body.queue_depth
    if body.camera_ok is not None: device.camera_ok = body.camera_ok
    db.commit()
    return {"status": "ok"}


@router.get("/commands")
def poll_commands(db: Session = Depends(get_db),
                  device: EdgeDevice = Depends(get_edge_device)):
    device.last_seen = utcnow()
    pending = db.query(EdgeCommand).filter(
        EdgeCommand.device_id == device.device_id,
        EdgeCommand.status == "pending").order_by(EdgeCommand.id).all()
    out = []
    for c in pending:
        c.status = "dispatched"
        c.acked_at = utcnow()
        out.append({"id": c.id, "command": c.command,
                    "payload": json.loads(c.payload) if c.payload else {},
                    "nonce": c.nonce})
    db.commit()
    return {"commands": out}


@router.post("/commands/{cmd_id}/ack")
def ack_command(cmd_id: int, body: AckIn, db: Session = Depends(get_db),
                device: EdgeDevice = Depends(get_edge_device)):
    c = db.query(EdgeCommand).filter(EdgeCommand.id == cmd_id,
                                     EdgeCommand.device_id == device.device_id).first()
    if not c:
        raise HTTPException(404, "Command not found")
    c.status = body.status if body.status in ("done", "failed") else "done"
    c.result = body.result
    c.acked_at = utcnow()
    db.commit()
    return {"status": c.status}


@router.post("/devices/{device_id}/commands")
def enqueue_command(device_id: str, body: CommandIn, db: Session = Depends(get_db),
                    user=Depends(require_position("administrator", "officer"))):
    dev = db.query(EdgeDevice).filter(EdgeDevice.device_id == device_id).first()
    if not dev:
        raise HTTPException(404, "Device not found")
    if body.command not in ALLOWED_COMMANDS:
        raise HTTPException(422, "Unknown command")
    c = EdgeCommand(device_id=device_id, command=body.command,
                    payload=json.dumps(body.payload or {}),
                    nonce=secrets.token_hex(8))
    db.add(c)
    db.commit()
    audit(db, user.id, "edge_command_enqueued", f"device={device_id} cmd={body.command}")
    return {"id": c.id, "nonce": c.nonce}


@router.post("/evidence")
async def edge_evidence(db: Session = Depends(get_db),
                        device: EdgeDevice = Depends(get_edge_device),
                        file: UploadFile = File(...),
                        event_id: str = Form(...),
                        violation_type: str = Form(...),
                        captured_at: str = Form(...),
                        confidence: float = Form(0.0),
                        sha256: str = Form(...),
                        plate_text: str | None = Form(None)):
    data = await file.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256.lower():
        raise HTTPException(400, "SHA-256 mismatch: chain of custody broken")
    if db.query(Violation).filter(Violation.event_id == event_id).first():
        raise HTTPException(409, "Duplicate event_id")

    ev_dir = Path(settings.STORAGE_ROOT) / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    path = ev_dir / f"{event_id}.jpg"
    path.write_bytes(data)

    try:
        cap = datetime.fromisoformat(captured_at)
    except ValueError:
        cap = utcnow()

    v = Violation(event_id=event_id, uid=device.device_id,
                  violation_type=violation_type, confidence=confidence,
                  captured_at=cap, status="pending",
                  image_path=str(path), evidence_path=str(path),
                  plate_text=plate_text,
                  plate_source="edge" if plate_text else None,
                  uploaded_by=device.device_id)
    db.add(v)
    device.last_seen = utcnow()
    db.commit()
    audit(db, None, "edge_evidence_ingested", f"device={device.device_id} event={event_id}")
    return {"id": v.id, "event_id": v.event_id, "sha256": digest}


@router.get("/status")
def edge_status(db: Session = Depends(get_db),
                user=Depends(require_position("administrator", "officer", "viewer"))):
    devs = db.query(EdgeDevice).all()
    return [{"device_id": d.device_id, "last_seen": d.last_seen,
             "camera_ok": d.camera_ok, "queue_depth": d.queue_depth} for d in devs]