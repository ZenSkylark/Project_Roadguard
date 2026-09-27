"""Batch OCR accuracy vs ground truth: python ocr_batch.py test_plates"""
import sys
from pathlib import Path
from backend.services.ocr import get_ocr

folder = Path(sys.argv[1] if len(sys.argv) > 1 else "test_plates")
ocr = get_ocr()
hits = total = 0

for f in sorted(folder.glob("synth_*.jpg")):
    truth = f.stem.split("_")[-1]          # synth_0_ABC1234 -> ABC1234
    res = ocr.read_plate(str(f))
    got = res.text if res else None
    ok = (got == truth)
    hits += ok
    total += 1
    conf = f"{res.confidence:.2f}" if res else "-"
    print(f"{'PASS' if ok else 'FAIL'}  {f.name:<28} expected={truth:<8} got={str(got):<8} conf={conf}")

print(f"\nAccuracy: {hits}/{total}")