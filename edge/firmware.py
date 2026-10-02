import uuid
from datetime import datetime

from .camera import StubCamera
from .spool import Spool
from .uplink import EdgeClient

IDLE, ARMED, CAPTURE, PROCESS, UPLOAD, ACK, SAFE = (
    "IDLE", "ARMED", "CAPTURE", "PROCESS", "UPLOAD", "ACK", "SAFE")


class EdgeFirmware:
    """State machine: IDLE -> CAPTURE -> PROCESS -> UPLOAD -> ACK, SAFE on fault."""

    def __init__(self, config, camera=None, client=None, spool=None):
        self.config = config
        self.camera = camera or StubCamera()
        self.client = client or EdgeClient(config)
        self.spool = spool or Spool(config.spool_dir)
        self.state = IDLE
        self.steps = 0

    def _new_event(self):
        return {
            "event_id": str(uuid.uuid4()),
            "violation_type": "illegal_parking",
            "captured_at": datetime.utcnow().isoformat(),
            "confidence": 0.87,
            "plate_text": None,
        }

    def step(self):
        self.steps += 1
        self._handle_commands()
        if self.steps % 5 == 0:
            self._send_telemetry()
        if self.spool.depth():
            self._flush_spool()
            return self.state
        if not self.config.armed:
            self.state = IDLE
            return self.state
        try:
            triggered = self.camera.detect()
        except RuntimeError:
            self.state = SAFE
            return self.state
        if triggered:
            self.state = CAPTURE
            try:
                frame = self.camera.capture()
            except RuntimeError:
                self.state = SAFE
                return self.state
            self.spool.add(self._new_event(), frame)
            self.state = PROCESS
            self._flush_spool()
        else:
            self.state = IDLE
        return self.state

    def _flush_spool(self):
        for path in self.spool.pending():
            event, frame = self.spool.load(path)
            ok, _code = self.client.upload(event, frame)
            if ok:
                self.spool.remove(event["event_id"])
                self.state = ACK
            else:
                self.state = UPLOAD
                break

    def _send_telemetry(self):
        self.client.telemetry({
            "firmware_version": self.config.firmware_version,
            "cpu_temp": 45.0, "cpu_load": 0.5, "disk_free": 1024.0,
            "queue_depth": self.spool.depth(),
            "camera_ok": self.state != SAFE,
        })

    def _handle_commands(self):
        for cmd in self.client.poll_commands():
            name = cmd["command"]
            try:
                if name == "capture_now":
                    self.spool.add(self._new_event(), self.camera.capture())
                    self._flush_spool()
                    self.client.ack(cmd["id"], "done", "ok")
                elif name == "set_mode":
                    self.config.armed = bool(cmd["payload"].get("armed", True))
                    self.client.ack(cmd["id"], "done", f"armed={self.config.armed}")
                elif name == "set_config":
                    for k, v in cmd["payload"].items():
                        if hasattr(self.config, k):
                            setattr(self.config, k, v)
                    self.client.ack(cmd["id"], "done", "config-updated")
                elif name == "reboot":
                    self.client.ack(cmd["id"], "done", "reboot-scheduled")
                else:
                    self.client.ack(cmd["id"], "failed", f"unsupported:{name}")
            except RuntimeError:
                self.client.ack(cmd["id"], "failed", "camera fault")
                self.state = SAFE

    def run(self, steps=10):
        for _ in range(steps):
            self.step()
        return self.state