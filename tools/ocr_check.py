"""Quick single-image OCR sanity check.

Usage:
    python tools/ocr_check.py <image_path>
"""
import sys
from pathlib import Path

from common import ocr_image


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")

    plate, conf = ocr_image(path)
    print("=" * 50)
    print(f"Image      : {path.name}")
    print(f"Plate text : {plate or '(none detected)'}")
    print(f"Confidence : {conf:.1f}%")
    print("=" * 50)


if __name__ == "__main__":
    main()