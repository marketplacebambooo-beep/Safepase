from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal, engine, Base
from app.models import BirthPrep, CHW, Facility, Pregnancy, User
from app.migrate import run_migrations


def seed():
    """Initial facility setup — run once via `python seed.py` or SEED_ON_STARTUP=true."""
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        if db.query(Facility).count():
            _ensure_birth_prep(db)
            _ensure_user_phones(db)
            _ensure_admin(db)
            _ensure_active_users(db)
            _reset_demo_passwords(db)
            db.commit()
            print("Database already initialized.")
            return

        mashava = Facility(name="Mashava Clinic", type="clinic", district="Gutu", phone="+263771000001")
        chatsworth = Facility(name="Chatsworth Clinic", type="clinic", district="Gutu", phone="+263771000002")
        gutu_hospital = Facility(name="Gutu District Hospital", type="hospital", district="Gutu", phone="+263771000003")
        db.add_all([mashava, chatsworth, gutu_hospital])
        db.flush()

        chw = CHW(name="Rudo Mupfumi", phone="+263771234567", village="Mashava", facility_id=mashava.id)
        db.add(chw)
        db.flush()

        nurse = User(
            email="chipo@mashava.clinic",
            password_hash=hash_password("changeme"),
            name="Sister Chipo",
            role="nurse",
            phone="+263771100001",
            facility_id=mashava.id,
        )
        hospital_user = User(
            email="farai@gutu.hospital",
            password_hash=hash_password("changeme"),
            name="Sister Farai",
            role="hospital",
            phone="+263771100002",
            facility_id=gutu_hospital.id,
        )
        admin_user = User(
            email="admin@safepass.co.zw",
            password_hash=hash_password("changeme"),
            name="SafePass Admin",
            role="admin",
            phone="+263771100000",
            facility_id=None,
        )
        db.add_all([nurse, hospital_user, admin_user])
        db.commit()
        print("Initial setup complete. Default password: changeme — update immediately.")
        print("Admin login: admin@safepass.co.zw / changeme")
    finally:
        db.close()


def _ensure_admin(db: Session):
    if not db.query(User).filter(User.role == "admin").first():
        db.add(
            User(
                email="admin@safepass.co.zw",
                password_hash=hash_password("changeme"),
                name="SafePass Admin",
                role="admin",
                phone="+263771100000",
            )
        )


def _ensure_user_phones(db: Session):
    defaults = {
        "chipo@mashava.clinic": "+263771100001",
        "farai@gutu.hospital": "+263771100002",
        "admin@safepass.co.zw": "+263771100000",
    }
    for email, phone in defaults.items():
        user = db.query(User).filter(User.email == email).first()
        if user and not user.phone:
            user.phone = phone


def _ensure_active_users(db: Session):
    for user in db.query(User).all():
        if user.is_active is None:
            user.is_active = True


def _reset_demo_passwords(db: Session):
    """Re-hash demo passwords so login works after bcrypt library changes."""
    demo_emails = ["chipo@mashava.clinic", "farai@gutu.hospital", "admin@safepass.co.zw"]
    for email in demo_emails:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.password_hash = hash_password("changeme")
            user.is_active = True


def _ensure_birth_prep(db: Session):
    for preg in db.query(Pregnancy).all():
        if not preg.birth_prep:
            db.add(BirthPrep(pregnancy_id=preg.id))


if __name__ == "__main__":
    seed()
