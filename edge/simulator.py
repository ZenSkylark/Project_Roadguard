import cv2
import requests
import uuid
import time
import os
from datetime import datetime
from collections import deque

# --- CONFIGURATION ---
API_URL = "http://localhost:8000/api/evidence"
LOGIN_URL = "http://localhost:8000/api/auth/login"

# 1. Login to get a token (Simulating the Pi authenticating itself)
print("Authenticating with server...")
res = requests.post(LOGIN_URL, data={"username": "admin", "password": "Admin123!"})
if res.status_code != 200:
    print("Login failed! Is the backend running?")
    exit()
TOKEN = res.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# 2. Setup the "Camera" (Webcam or Dummy Feed)
cap = cv2.VideoCapture(0)
use_dummy = not cap.isOpened()
if use_dummy:
    print("Webcam not found. Using simulated dummy video feed.")

# Ring Buffer (Simulating the Pi's RAM buffer)
buffer = deque(maxlen=60) 

print("\n--- EDGE SIMULATOR ACTIVE ---")
print("Press 'v' to simulate a VIOLATION")
print("Press 'q' to quit")
print("-----------------------------\n")

while True:
    if not use_dummy:
        ret, frame = cap.read()
        if not ret:
            break
    else:
        # Generate a dummy frame if no webcam is available
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "SIMULATED DASHCAM FEED", (50, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", (50, 300), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    buffer.append(frame)

    # Display the feed (This is what the Pi "sees")
    cv2.imshow("Roadguard Edge Simulator (Press 'v' for Violation)", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('v'):
        print("\n[!] VIOLATION DETECTED! (User triggered 'v')")
        print("Capturing evidence and uploading to server...")
        
        # Simulate the "best frame" (the one at the moment of violation)
        evidence_frame = buffer[-1]
        filename = f"sim_{uuid.uuid4().hex[:8]}.jpg"
        cv2.imwrite(filename, evidence_frame)

        # Upload to Backend
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'image/jpeg')}
            data = {
                'event_id': f"sim-{int(time.time())}",
                'violation_type': 'tailgating', # Simulated violation type
                'confidence': '0.88',
                'captured_at': datetime.utcnow().isoformat()
            }

            r = requests.post(API_URL, headers=HEADERS, files=files, data=data)

        # Cleanup temp file
        os.remove(filename)

        if r.status_code == 201:
            print(f"[+] SUCCESS: Event {data['event_id']} uploaded! Check Dashboard.")
        else:
            print(f"[-] FAILED: {r.status_code} {r.text}")

cap.release()
cv2.destroyAllWindows()