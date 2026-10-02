"""Run OCR over a folder of images and print a summary table.

Usage:
    python tools/ocr_batch.py [image_folder]

Defaults to <project_root>/test_plates. If ground_truth.txt exists in
the folder (filename<space>expected), results are graded for accuracy.
"""
import sys
from pathlib import Path

from common import PROJECT_ROOT, ocr_image


def main():
    folder = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PROJECT_ROOT / "test_plates"
    if not folder.is_dir():
        sys.exit(f"❌ Folder not found: {folder}")

    gt = {}
    gt_file = folder / "ground_truth.txt"
    if gt_file.exists():
        for line in gt_file.read_text(encoding="utf-8").splitlines():
            name, _, expected = line.partition(" ")
            gt[name.strip()] = expected.strip()

    images = sorted(list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png")))
    if not images:
        sys.exit(f"❌ No images found in {folder}")

    print(f"{'File':<28} {'OCR result':<14} {'Conf':>7}  Grade")
    print("-" * 62)
    passed = graded = 0
    for img in images:
        plate, conf = ocr_image(img)
        grade = ""
        expected = gt.get(img.name)
        if expected:
            graded += 1
            ok = expected.upper() in plate
            passed += ok
            grade = "✅" if ok else f"❌ expected {expected}"
        print(f"{img.name:<28} {plate or '-':<14} {conf:>6.1f}%  {grade}")

    print("-" * 62)
    print(f"Processed {len(images)} image(s).")
    if graded:
        print(f"Accuracy: {passed}/{graded} ({100 * passed / graded:.0f}%)")


if __name__ == "__main__":
    main()