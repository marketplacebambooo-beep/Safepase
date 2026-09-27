from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password
from app.database import get_db
from app.models import CHW, Facility, User
from app.schemas import (
    CHWCreate,
    CHWOut,
    CHWUpdate,
    FacilityCreate,
    FacilityOut,
    FacilityUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.audit import log_action
from app.services.edd_reminders import run_edd_reminders
from app.services.permissions import require_roles
from app.services.phone import normalize_phone

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        phone=user.phone,
        facility_id=user.facility_id,
        facility_name=user.facility.name if user.facility else None,
    )


@router.get("/facilities", response_model=list[FacilityOut])
def admin_list_facilities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    return db.query(Facility).order_by(Facility.name).all()


@router.post("/facilities", response_model=FacilityOut)
def create_facility(
    body: FacilityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin")
    facility = Facility(
        name=body.name,
        type=body.type,
        district=body.district,
        phone=normalize_phone(body.phone),
    )
    db.add(facility)
    log_action(db, user, "create", "facility", detail=body.name)
    db.commit()
    db.refresh(facility)
    return facility


@router.patch("/facilities/{facility_id}", response_model=FacilityOut)
def update_facility(
    facility_id: int,
    body: FacilityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin")
    facility = db.get(Facility, facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "phone":
            value = normalize_phone(value)
        setattr(facility, field, value)
    log_action(db, user, "update", "facility", facility_id)
    db.commit()
    db.refresh(facility)
    return facility


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    return [_user_out(u) for u in db.query(User).order_by(User.name).all()]


@router.post("/users", response_model=UserOut)
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    if body.role not in ("nurse", "hospital", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
        phone=normalize_phone(body.phone),
        facility_id=body.facility_id,
    )
    db.add(new_user)
    log_action(db, user, "create", "user", detail=body.email)
    db.commit()
    db.refresh(new_user)
    return _user_out(new_user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "phone":
            value = normalize_phone(value)
        setattr(target, field, value)
    log_action(db, user, "update", "user", user_id)
    db.commit()
    db.refresh(target)
    return _user_out(target)


@router.get("/chws", response_model=list[CHWOut])
def admin_list_chws(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    return db.query(CHW).order_by(CHW.name).all()


@router.post("/chws", response_model=CHWOut)
def create_chw(body: CHWCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    phone = normalize_phone(body.phone)
    if db.query(CHW).filter(CHW.phone == phone).first():
        raise HTTPException(status_code=400, detail="CHW phone already registered")
    chw = CHW(name=body.name, phone=phone, village=body.village, facility_id=body.facility_id)
    db.add(chw)
    log_action(db, user, "create", "chw", detail=body.name)
    db.commit()
    db.refresh(chw)
    return chw


@router.patch("/chws/{chw_id}", response_model=CHWOut)
def update_chw(
    chw_id: int,
    body: CHWUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin")
    chw = db.get(CHW, chw_id)
    if not chw:
        raise HTTPException(status_code=404, detail="CHW not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "phone":
            value = normalize_phone(value)
            if db.query(CHW).filter(CHW.phone == value, CHW.id != chw_id).first():
                raise HTTPException(status_code=400, detail="Phone already in use")
        setattr(chw, field, value)
    log_action(db, user, "update", "chw", chw_id)
    db.commit()
    db.refresh(chw)
    return chw


@router.post("/run-edd-reminders")
def trigger_edd_reminders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    result = run_edd_reminders(db)
    log_action(db, user, "run", "edd_reminders", detail=str(result))
    return result
