import json
from pathlib import Path


class Spool:
    """Bounded offline buffer: survives uplink outages."""
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def add(self, event, image_bytes):
        eid = event["event_id"]
        (self.dir / f"{eid}.json").write_text(json.dumps(event))
        (self.dir / f"{eid}.bin").write_bytes(image_bytes)

    def pending(self):
        return sorted(self.dir.glob("*.json"))

    def load(self, path):
        event = json.loads(path.read_text())
        frame = (self.dir / f"{event['event_id']}.bin").read_bytes()
        return event, frame

    def remove(self, event_id):
        for ext in (".json", ".bin"):
            p = self.dir / f"{event_id}{ext}"
            if p.exists():
                p.unlink()

    def depth(self):
        return len(list(self.dir.glob("*.json")))