import sys
from paddleocr import PaddleOCR

if len(sys.argv) < 2:
    print("Usage: python ocr_debug.py <image_path>")
    sys.exit(1)

ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
results = ocr.ocr(sys.argv[1], cls=True)

print("\n--- RAW PADDLEOCR OUTPUT ---")
if results and results[0]:
    for line in results[0]:
        text = line[1][0]
        conf = float(line[1][1])
        print(f"Text: '{text}'  |  Confidence: {conf:.2f}")
else:
    print("❌ PaddleOCR found absolutely no text in this image.")