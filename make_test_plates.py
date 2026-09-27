"""Renders synthetic PH plates embedded in a dashcam-like scene."""
import cv2
import numpy as np
import random
import string
from pathlib import Path

OUT = Path("test_plates")
OUT.mkdir(exist_ok=True)

for i in range(5):
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = str(random.randint(1000, 9999))
    plate = letters + digits

    # 1280x720 blurry "street" canvas
    scene = np.random.randint(60, 120, (720, 1280, 3), np.uint8)
    scene = cv2.GaussianBlur(scene, (15, 15), 0)

    # plate region ~520x170, centered
    px, py, pw, ph = 380, 280, 520, 170
    plate_img = np.full((ph, pw, 3), 235, np.uint8)
    cv2.rectangle(plate_img, (6, 6), (pw - 7, ph - 7), (30, 30, 30), 4)
    cv2.putText(plate_img, f"{letters} {digits}", (48, 122),
                cv2.FONT_HERSHEY_SIMPLEX, 2.2, (15, 15, 15), 6)
    plate_img = cv2.GaussianBlur(plate_img, (3, 3), 0)
    noise = np.random.randint(-10, 10, plate_img.shape, np.int16)
    plate_img = np.clip(plate_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    scene[py:py + ph, px:px + pw] = plate_img
    path = OUT / f"synth_{i}_{plate}.jpg"
    cv2.imwrite(str(path), scene)
    print(f"{path}  ->  ground truth: {plate}")