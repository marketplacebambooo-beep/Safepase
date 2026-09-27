from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Pregnancy, Referral, User


def require_roles(user: User, *roles: str):
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def can_view_pregnancy(db: Session, user: User, pregnancy: Pregnancy) -> bool:
    if user.role == "admin":
        return True
    if user.role == "nurse" and user.facility_id and pregnancy.clinic_id == user.facility_id:
        return True
    if user.role == "hospital" and user.facility_id:
        return (
            db.query(Referral)
            .filter(
                Referral.pregnancy_id == pregnancy.id,
                Referral.to_facility_id == user.facility_id,
            )
            .first()
            is not None
        )
    return False


def assert_pregnancy_access(db: Session, user: User, pregnancy: Pregnancy):
    if not can_view_pregnancy(db, user, pregnancy):
        raise HTTPException(status_code=403, detail="Access denied")


def assert_clinic_nurse(user: User, pregnancy: Pregnancy):
    if user.role != "nurse" or not user.facility_id or pregnancy.clinic_id != user.facility_id:
        raise HTTPException(status_code=403, detail="Clinic access required")


def assert_hospital_referral(user: User, referral: Referral):
    if user.role not in ("hospital", "admin"):
        raise HTTPException(status_code=403, detail="Hospital access required")
    if user.role == "hospital" and referral.to_facility_id != user.facility_id:
        raise HTTPException(status_code=403, detail="Access denied")
