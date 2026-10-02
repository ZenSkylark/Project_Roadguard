"""Generate synthetic license-plate images for OCR testing.

Usage:
    python tools/make_test_plates.py [--count N] [--out DIR]

Writes images plus ground_truth.txt (filename<space>plate) into the
output folder (default: <project_root>/test_plates).
"""
import argparse
import random
import string
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow is required: pip install pillow")

from common import PROJECT_ROOT


def random_plate(rng):
    letters = "".join(rng.choices(string.ascii_uppercase, k=3))
    digits = "".join(rng.choices(string.digits, k=4))
    return f"{letters}{digits}"


def draw_plate(text, path):
    w, h = 400, 120
    img = Image.new("RGB", (w, h), (240, 240, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, w - 5, h - 5], outline=(20, 20, 20), width=3)

    font = None
    for candidate in ("C:/Windows/Fonts/arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(candidate, 64)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]), text, fill=(10, 10, 10), font=font)
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description="Generate test license plates")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "test_plates")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    manifest = []
    for i in range(args.count):
        text = random_plate(rng)
        path = args.out / f"plate_{i:02d}_{text}.jpg"
        draw_plate(text, path)
        manifest.append((path.name, text))

    (args.out / "ground_truth.txt").write_text(
        "\n".join(f"{name} {text}" for name, text in manifest), encoding="utf-8")

    print(f"✅ Generated {args.count} plates in {args.out}")
    print(f"   Ground truth: {args.out / 'ground_truth.txt'}")


if __name__ == "__main__":
    main()