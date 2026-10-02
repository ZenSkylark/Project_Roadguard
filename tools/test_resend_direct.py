"""Send a test email through Resend WITHOUT starting the FastAPI app.

Usage:
    python tools/test_resend_direct.py [to_email]

Requires in .env:
    RESEND_API_KEY=...
    RESEND_FROM=...    (optional; defaults to onboarding@resend.dev)
"""
import os
import sys

import httpx

from common import load_env

load_env()


def main():
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        sys.exit("❌ RESEND_API_KEY not set in .env")

    to = sys.argv[1] if len(sys.argv) > 1 else "dev@roadguard.ph"
    sender = os.environ.get("RESEND_FROM", "onboarding@resend.dev")

    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "from": f"Roadguard <{sender}>",
            "to": [to],
            "subject": "Roadguard Resend direct test",
            "text": "If you can read this, Resend sending works.",
        },
        timeout=15,
    )
    print(f"Status: {r.status_code}")
    print(r.text)
    if r.status_code in (200, 201):
        print("✅ Resend test email accepted.")
    else:
        sys.exit("❌ Resend send failed.")


if __name__ == "__main__":
    main()