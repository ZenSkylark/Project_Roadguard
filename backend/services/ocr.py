import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from ..config import settings

@dataclass
class PlateResult:
    text: str
    confidence: float

class OCRStrategy(ABC):
    @abstractmethod
    def read_plate(self, image_path: str) -> PlateResult | None: ...

class StubOCRStrategy(OCRStrategy):
    """Dev stand-in: filename containing 'plate' = readable, else unreadable."""
    def read_plate(self, image_path: str):
        return PlateResult("ABC1234", 0.95) if "plate" in Path(image_path).name.lower() else None

class PaddleOCRStrategy(OCRStrategy):
    PLATE_RE = re.compile(r"^[A-Z]{3}\s?\d{3,4}$")
    def __init__(self):
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    def read_plate(self, image_path: str):
        best = None
        for page in self._ocr.ocr(image_path, cls=True):
            for line in (page or []):
                text = re.sub(r"[^A-Za-z0-9]", "", line[1][0]).upper()
                conf = float(line[1][1])
                if self.PLATE_RE.match(text) and (best is None or conf > best.confidence):
                    best = PlateResult(text, conf)
        return best

def get_ocr() -> OCRStrategy:
    return PaddleOCRStrategy() if settings.OCR_BACKEND == "paddle" else StubOCRStrategy()