"""Verify live Africa's Talking SMS credentials.

Usage:
  python test_live_at.py +26377xxxxxxx
"""
import sys

import httpx
from urllib.parse import urlencode

from app.config import settings
from app.services.channels import build_channel_status
from app.services.phone import normalize_phone


def main():
    status = build_channel_status()
    print("Channel status:")
    for issue in status.get("issues", []):
        print(f"  ! {issue}")
    if not status.get("credentials_configured"):
        print("\nSet AT_USERNAME and AT_API_KEY in .env (live account, not sandbox).")
        sys.exit(1)
    if status.get("at_username") == "sandbox":
        print("\nAT_USERNAME is still 'sandbox'. Use your LIVE app username for physical phones.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("\nUsage: python test_live_at.py <phone>")
        print("Example: python test_live_at.py +263771234567")
        sys.exit(1)

    phone = normalize_phone(sys.argv[1])
    if not phone:
        print("Invalid phone number.")
        sys.exit(1)

    message = "SafePass live test: Africa's Talking SMS is working."
    payload = urlencode({
        "username": settings.at_username,
        "to": phone,
        "message": message,
        "from": settings.sms_sender_id,
    })
    print(f"\nSending test SMS to {phone} from {settings.sms_sender_id}...")
    resp = httpx.post(
        "https://api.africastalking.com/version1/messaging",
        content=payload,
        headers={
            "apiKey": settings.at_api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=20.0,
    )
    print(f"HTTP {resp.status_code}")
    print(resp.text)
    if resp.status_code == 201:
        print("\nSuccess — check your physical phone for the SMS.")
    else:
        print("\nFailed — check sender ID approval and account balance.")


if __name__ == "__main__":
    main()
