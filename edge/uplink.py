import hashlib
import httpx


class EdgeClient:
    def __init__(self, config, client=None):
        self.config = config
        self._client = client or httpx.Client(base_url=config.server_url, timeout=10)
        self._client.headers["X-Edge-Key"] = config.device_key

    def telemetry(self, payload):
        r = self._client.post("/api/edge/telemetry", json=payload)
        return r.status_code == 200

    def poll_commands(self):
        r = self._client.get("/api/edge/commands")
        if r.status_code != 200:
            return []
        return r.json().get("commands", [])

    def ack(self, cmd_id, status="done", result=None):
        r = self._client.post(f"/api/edge/commands/{cmd_id}/ack",
                              json={"status": status, "result": result})
        return r.status_code == 200

    def upload(self, event, image_bytes):
        sha = hashlib.sha256(image_bytes).hexdigest()
        files = {"file": ("frame.jpg", image_bytes, "image/jpeg")}
        data = {k: str(v) for k, v in event.items() if v is not None}
        data["sha256"] = sha
        r = self._client.post("/api/edge/evidence", files=files, data=data)
        return r.status_code in (200, 201), r.status_code