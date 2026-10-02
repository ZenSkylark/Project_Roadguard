class StubCamera:
    """Deterministic camera for dev/tests. Real CSI driver comes later."""
    def __init__(self, script=None):
        self.script = list(script or [])
        self.fail = False

    def detect(self):
        if self.fail:
            raise RuntimeError("camera fault")
        if self.script:
            return bool(self.script.pop(0))
        return False

    def capture(self):
        if self.fail:
            raise RuntimeError("camera fault")
        return b"\xff\xd8\xff\xe0stubframe"