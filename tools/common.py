"""Shared helpers for Roadguard developer tools.

All tools resolve paths relative to the repository root, so they can be
run from ANY working directory:

    python tools/ocr_check.py img.jpg
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent


def load_env():
    """Load .env from the project root into os.environ (never overrides)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_ocr():
    """Import OCR dependencies or exit with install hints."""
    try:
        from PIL import Image
        import pytesseract
        from pytesseract import Output
    except ImportError:
        sys.exit(
            "OCR dependencies missing.\n"
            "Activate the server environment and install:\n"
            "  server_env\\Scripts\\Activate.ps1\n"
            "  pip install pillow pytesseract\n"
            "Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    # Auto-locate tesseract.exe on Windows
    import os
    candidates = [
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Users\Zen\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\tools\tesseract\tesseract.exe",
    ]
    for cand in candidates:
        if cand and Path(cand).exists():
            pytesseract.pytesseract.tesseract_cmd = cand
            break
    else:
        # Fall back to PATH; pytesseract will raise a clear error if missing
        pass

    return Image, pytesseract, Output


def ocr_image(path):
    """Return (plate_text, mean_confidence) for one image."""
    Image, pytesseract, Output = require_ocr()
    img = Image.open(path)
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    words, confs = [], []
    for text, conf in zip(data["text"], data["conf"]):
        if text.strip():
            words.append(text.strip())
            try:
                c = float(conf)
            except (TypeError, ValueError):
                c = -1.0
            if c > 0:
                confs.append(c)
    plate = "".join(words).upper()
    mean = sum(confs) / len(confs) if confs else 0.0
    return plate, mean


def ocr_words(path):
    """Return (rows, img) where rows = (text, conf, left, top, width, height)."""
    Image, pytesseract, Output = require_ocr()
    img = Image.open(path)
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    rows = []
    for text, conf, l, t, w, h in zip(
        data["text"], data["conf"], data["left"], data["top"], data["width"], data["height"]
    ):
        if text.strip():
            rows.append((text.strip(), conf, l, t, w, h))
    return rows, img