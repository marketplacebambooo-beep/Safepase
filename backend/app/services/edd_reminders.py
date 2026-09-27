import logging
from datetime import date

from sqlalchemy.orm import Session

from app.i18n.messages import t
from app.models import Notification, Pregnancy
from app.services.notifications import notify_user, send_patient_message

logger = logging.getLogger(__name__)

EDD_KEYS = {7: "edd_7", 1: "edd_1", 0: "edd_0"}


def _already_sent(db: Session, pregnancy_id: int, days_before: int) -> bool:
    key = EDD_KEYS.get(days_before, "edd_0")
    prefix = t(key, "en", ref="")[:20]
    return (
        db.query(Notification)
        .filter(Notification.pregnancy_id == pregnancy_id, Notification.message.like(f"{prefix}%"))
        .first()
        is not None
    )


def run_edd_reminders(db: Session) -> dict:
    today = date.today()
    sent = 0
    skipped = 0

    pregnancies = (
        db.query(Pregnancy)
        .filter(Pregnancy.status == "active", Pregnancy.edd.isnot(None), Pregnancy.phone.isnot(None))
        .all()
    )

    for pregnancy in pregnancies:
        days_until = (pregnancy.edd - today).days
        if days_until not in EDD_KEYS:
            continue
        if _already_sent(db, pregnancy.id, days_until):
            skipped += 1
            continue

        msg = t(EDD_KEYS[days_until], pregnancy.language, ref=pregnancy.ref_number)
        send_patient_message(db, pregnancy, msg)

        if pregnancy.clinic_id:
            from app.models import User

            nurses = db.query(User).filter(User.role == "nurse", User.facility_id == pregnancy.clinic_id).all()
            for nurse in nurses:
                notify_user(
                    db,
                    nurse,
                    f"EDD reminder ({days_until}d): {pregnancy.first_name} {pregnancy.last_name}. Ref {pregnancy.ref_number}.",
                    pregnancy_id=pregnancy.id,
                )

        sent += 1

    db.commit()
    return {"sent": sent, "skipped": skipped, "checked": len(pregnancies)}
