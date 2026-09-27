"""Usage: python ocr_check.py path\to\plate_photo.jpg"""
import sys
from backend.config import settings
from backend.services.ocr import get_ocr

if len(sys.argv) < 2:
    print("Usage: python ocr_check.py <image_path>")
    sys.exit(1)

print(f"OCR backend: {settings.OCR_BACKEND}")
print(f"Result: {get_ocr().read_plate(sys.argv[1])}")