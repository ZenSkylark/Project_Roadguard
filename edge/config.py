from dataclasses import dataclass


@dataclass
class EdgeConfig:
    server_url: str = "http://127.0.0.1:8000"
    device_id: str = "edge-01"
    device_key: str = ""
    spool_dir: str = "./edge_spool"
    camera_mode: str = "stub"   # "stub" for dev/tests, "csi" on Orange Pi 5 Plus
    armed: bool = True
    firmware_version: str = "0.1.0"