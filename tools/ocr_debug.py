"""Verbose OCR debugging: image stats, preprocessing stages, per-word boxes.

Usage:
    python tools/ocr_debug.py <image_path>

Saves grayscale and threshold stages next to the image as
<name>_debug_1_gray.png / <name>_debug_2_thresh.png and compares OCR
output across stages.
"""
import sys
from pathlib import Path

from common import ocr_words, require_ocr


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")

    rows, img = ocr_words(path)
    Image, pytesseract, _ = require_ocr()

    print("=" * 64)
    print(f"Image : {path}")
    print(f"Size  : {img.size[0]}x{img.size[1]}  Mode: {img.mode}")
    print("=" * 64)

    gray = img.convert("L")
    thresh = gray.point(lambda p: 255 if p > 128 else 0)
    stages = [("gray", gray), ("thresh", thresh)]

    for label, im in stages:
        out = path.parent / f"{path.stem}_debug_{label}.png"
        im.save(out)
        print(f"Saved stage: {out}")

    print("-" * 64)
    print(f"{'Word':<12} {'Conf':>6}  Box (left,top,w,h)")
    for text, conf, l, t, w, h in rows:
        print(f"{text:<12} {conf:>6}  ({l},{t},{w},{h})")

    plate = "".join(t for t, *_ in rows).upper()
    print("-" * 64)
    print(f"Combined plate: {plate or '(none)'}")

    for label, im in stages:
        raw = pytesseract.image_to_string(im).strip()
        print(f"OCR[{label}]: {raw or '(none)'}")


if __name__ == "__main__":
    main()