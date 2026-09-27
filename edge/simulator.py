import cv2
import requests
import uuid
import time
import os
import random
from datetime import datetime
from collections import deque
from pathlib import Path

# --- CONFIGURATION ---
API_URL = "http://localhost:8000/api/evidence"
LOGIN_URL = "http://localhost:8000/api/auth/login"
VERIFY_URL = "http://localhost:8000/api/auth/mfa/verify"
USERNAME = "admin"
PASSWORD = "Admin123!"
ROOT = Path(__file__).resolve().parent.parent      # Software/ no matter the CWD
SYNTH_PLATES = sorted((ROOT / "test_plates").glob("synth_*.jpg"))


# 1. Login (SMS-MFA aware)
print("Authenticating with server...")
res = requests.post(LOGIN_URL, data={"username": USERNAME, "password": PASSWORD})
if res.status_code != 200:
    print("Login failed! Is the backend running?")
    print(res.text)
    exit()
payload = res.json()
if payload.get("mfa_required"):
    code = input("SMS code required -> check backend console for [DEV SMS], enter code: ")
    v = requests.post(VERIFY_URL,
                      json={"mfa_token": payload["mfa_token"], "code": code})
    if v.status_code != 200:
        print("MFA verification failed:", v.text)
        exit()
    payload = v.json()
TOKEN = payload["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("Authenticated.")
print(f"Synthetic plates available: {len(SYNTH_PLATES)}")
if not SYNTH_PLATES:
    print("WARNING: no synth_*.jpg in test_plates/ -> 'p' will behave like 'v'")


# 2. Setup the "Camera"
cap = cv2.VideoCapture(0)
use_dummy = not cap.isOpened()
if not use_dummy:
    for _ in range(10):          # discard dark warm-up frames
        cap.read()
else:
    print("Webcam not found. Using simulated dummy video feed.")

buffer = deque(maxlen=60)

print("\n--- EDGE SIMULATOR ACTIVE ---")
print("Press 'p' -> violation with READABLE plate (uploads a synth plate photo)")
print("Press 'v' -> violation with UNREADABLE plate (uploads live frame)")
print("Press 'q' -> quit")
print("-----------------------------\n")

while True:
    if not use_dummy:
        ret, frame = cap.read()
        if not ret:
            break
    else:
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "SIMULATED DASHCAM FEED", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", (50, 300),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    buffer.append(frame)
    cv2.imshow("Roadguard Edge Simulator (p=readable v=unreadable q=quit)", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in (ord('v'), ord('p')):
        readable = (key == ord('p'))
        tmp_path = None
        if readable and SYNTH_PLATES:
            src = random.choice(SYNTH_PLATES)
            truth = src.stem.split("_")[-1]
            fh = open(src, "rb")
            send_name = f"plate_{src.name}"       # 'plate' prefix also satisfies stub engine
            print(f"\n[!] VIOLATION with READABLE plate (ground truth: {truth})")
        else:
            tmp_path = f"sim_{uuid.uuid4().hex[:8]}.jpg"
            cv2.imwrite(tmp_path, buffer[-1])
            fh = open(tmp_path, "rb")
            send_name = tmp_path
            print("\n[!] VIOLATION with UNREADABLE plate (live frame)")

        with fh:
            files = {'file': (send_name, fh, 'image/jpeg')}
            data = {
                'event_id': f"sim-{int(time.time())}",
                'violation_type': random.choice(
                    ["tailgating", "running_red_light", "illegal_parking"]),
                'confidence': '0.88',
                'captured_at': datetime.now().isoformat(),
            }
            r = requests.post(API_URL, headers=HEADERS, files=files, data=data)

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

        if r.status_code == 201:
            body = r.json()
            print(f"[+] SUCCESS: plate={body.get('plate')} dir={body.get('directory')} -> dashboard!")
        else:
            print(f"[-] FAILED: {r.status_code} {r.text}")

cap.release()
cv2.destroyAllWindows()