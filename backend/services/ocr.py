import re, logging, cv2, sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from ..config import settings

@dataclass
class PlateResult:
    text: str
    confidence: float

# ---------------- shared preprocessing ----------------
def preprocess_plate(image_path: str, target_height: int | None = None) -> np.ndarray:
    """Grayscale -> upscale small plates -> CLAHE contrast."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if target_height and h < target_height:
        scale = target_height / h
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def normalize_plate_text(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()

# ---------------- strategies ----------------
class OCRStrategy(ABC):
    @abstractmethod
    def read_plate(self, image_path: str) -> PlateResult | None: ...

class StubOCRStrategy(OCRStrategy):
    """Dev/test stand-in: filename containing 'plate' = readable."""
    def read_plate(self, image_path: str):
        return PlateResult("ABC1234", 0.95) if "plate" in Path(image_path).name.lower() else None

class PaddleOCRStrategy(OCRStrategy):
    """General-purpose OCR engine (PaddleOCR 2.9.x, PP-OCRv4)."""
    def __init__(self):
        # Silence the noisy Paddle logger
        logging.getLogger('ppocr').setLevel(logging.ERROR)
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def read_plate(self, image_path: str):
        best = None
        # .ocr() returns a list of pages, each page is a list of lines
        # Each line is: [ [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ], (text, confidence) ]
        for page in self._ocr.ocr(image_path, cls=True):
            for line in (page or []):
                text = normalize_plate_text(line[1][0])
                conf = float(line[1][1])
                if PLATE_RE.match(text) and (best is None or conf > best.confidence):
                    best = PlateResult(text, conf)
        return best

class TrainedOCRStrategy(OCRStrategy):
    """Inference contract for YOUR custom plate CRNN (trained later in the AI branch)."""
    ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    HEIGHT, WIDTH = 32, 96

    def __init__(self):
        import onnxruntime as ort
        path = Path(settings.TRAINED_OCR_PATH)
        if not path.exists():
            raise FileNotFoundError(
                f"Trained OCR selected but no model at {path}. "
                "Train & export it in the AI branch first.")
        self._session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    def _tensor(self, gray: np.ndarray) -> np.ndarray:
        img = cv2.resize(gray, (self.WIDTH, self.HEIGHT), interpolation=cv2.INTER_AREA)
        img = (img.astype(np.float32) / 255.0 - 0.5) / 0.5
        return img[np.newaxis, np.newaxis, ...]

    def _ctc_decode(self, logits: np.ndarray) -> str:
        preds = np.argmax(logits[:, 0, :], axis=-1)
        chars, prev = [], -1
        for idx in preds:
            if idx != 0 and idx != prev:
                chars.append(self.ALPHABET[int(idx) - 1])
            prev = idx
        return "".join(chars)

    def read_plate(self, image_path: str):
        gray = preprocess_plate(image_path, target_height=self.HEIGHT)
        logits = self._session.run(
            None, {self._session.get_inputs()[0].name: self._tensor(gray)})[0]
        text = self._ctc_decode(logits)
        if PLATE_RE.match(text):
            return PlateResult(text, 0.90)
        return None

# ---------------- factory with lazy cache ----------------
_cache: dict[str, OCRStrategy] = {}

def get_ocr() -> OCRStrategy:
    key = settings.OCR_BACKEND
    if key not in _cache:
        if key == "paddle":
            _cache[key] = PaddleOCRStrategy()
        elif key == "trained":
            _cache[key] = TrainedOCRStrategy()
        elif key == "stub":
            _cache[key] = StubOCRStrategy()
        else:
            raise ValueError(f"Unknown OCR_BACKEND: {key}")
    return _cache[key]

def reset_ocr_cache():
    _cache.clear()

if sys.platform == "win32":
    import pytesseract
    _default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if _default.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_default)
PLATE_RE = re.compile(r"^[A-Z]{3}\s?\d{3,4}$")
