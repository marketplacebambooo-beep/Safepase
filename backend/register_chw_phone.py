"""Register your physical phone as the demo CHW for USSD testing.

Usage:
  python register_chw_phone.py +26377xxxxxxx
  python register_chw_phone.py 077xxxxxxx
"""
import sys

from app.database import SessionLocal
from app.models import CHW
from app.services.phone import normalize_phone


def main():
    if len(sys.argv) < 2:
        print("Usage: python register_chw_phone.py <your-phone>")
        print("Example: python register_chw_phone.py +263771234567")
        sys.exit(1)

    phone = normalize_phone(sys.argv[1])
    if not phone:
        print("Invalid phone number.")
        sys.exit(1)

    db = SessionLocal()
    try:
        chw = db.query(CHW).first()
        if not chw:
            print("No CHW in database. Run: python seed.py")
            sys.exit(1)
        old = chw.phone
        chw.phone = phone
        db.commit()
        print(f"CHW '{chw.name}' phone updated: {old} -> {phone}")
        print("This number can now use USSD on your Africa's Talking channel.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
