import logging

from sqlalchemy.orm import Session, joinedload

from app.models import Pregnancy, User
from app.services.care_pathway import build_care_pathway, get_care_flags
from app.services.notifications import notify_user, send_patient_message
from app.i18n.messages import t

logger = logging.getLogger(__name__)

ALERT_PREFIX = "SafePass follow-up:"


def _already_sent(db: Session, pregnancy_id: int, code: str) -> bool:
    from app.models import Notification

    marker = f"{ALERT_PREFIX} {code}"
    return (
        db.query(Notification)
        .filter(
            Notification.pregnancy_id == pregnancy_id,
            Notification.message.like(f"{marker}%"),
        )
        .first()
        is not None
    )


def _notify_nurses(db: Session, pregnancy: Pregnancy, code: str, message: str):
    if not pregnancy.clinic_id:
        return
    nurses = db.query(User).filter(User.role == "nurse", User.facility_id == pregnancy.clinic_id).all()
    full = f"{ALERT_PREFIX} {code} — {message}"
    for nurse in nurses:
        notify_user(db, nurse, full, pregnancy_id=pregnancy.id)


def notify_registration_pathway(db: Session, pregnancy: Pregnancy):
    """Immediate nurse alerts when a high-priority care pathway is opened."""
    flags = get_care_flags(pregnancy)
    name = f"{pregnancy.first_name} {pregnancy.last_name}"
    ref = pregnancy.ref_number

    if "adolescent" in flags:
        _notify_nurses(
            db,
            pregnancy,
            "new_adolescent",
            f"Under-18 pregnancy registered: {name}. Ref {ref}. Schedule enhanced ANC follow-up.",
        )
    if "twins" in flags:
        _notify_nurses(
            db,
            pregnancy,
            "new_twins",
            f"Multiple gestation registered: {name}. Ref {ref}. Elevated risk — plan hospital delivery.",
        )
    if "guardian_consent_pending" in flags:
        _notify_nurses(
            db,
            pregnancy,
            "guardian_consent",
            f"Guardian consent pending for {name}. Ref {ref}. Record at next clinic visit.",
        )
    if "post_term" in flags:
        _notify_nurses(
            db,
            pregnancy,
            "post_term",
            f"Post-term pregnancy: {name}. Ref {ref}. Escalate monitoring immediately.",
        )
    if "first_pregnancy" in flags:
        _notify_nurses(
            db,
            pregnancy,
            "new_primigravida",
            f"First pregnancy registered: {name}. Ref {ref}. Schedule birth-prep counselling and ANC education.",
        )


def run_follow_up_reminders(db: Session) -> dict:
    """Scheduled job — nurse SMS + patient messages for overdue care-pathway actions."""
    sent = 0
    skipped = 0

    pregnancies = (
        db.query(Pregnancy)
        .options(joinedload(Pregnancy.birth_prep))
        .filter(Pregnancy.status == "active")
        .all()
    )

    for pregnancy in pregnancies:
        pathway = build_care_pathway(db, pregnancy)
        for task in pathway["follow_up_tasks"]:
            code = task["code"]
            if _already_sent(db, pregnancy.id, code):
                skipped += 1
                continue

            priority = task["priority"]
            if priority not in ("high", "emergency"):
                continue

            nurse_msg = (
                f"{task['title']}: {pregnancy.first_name} {pregnancy.last_name}. "
                f"Ref {pregnancy.ref_number}. {task['detail'][:120]}"
            )
            _notify_nurses(db, pregnancy, code, nurse_msg)

            if pregnancy.phone and code in ("adolescent_early_anc", "post_term_escalation"):
                if code == "post_term_escalation":
                    patient_msg = t("followup_post_term", pregnancy.language, ref=pregnancy.ref_number)
                else:
                    patient_msg = t("followup_adolescent_anc", pregnancy.language, ref=pregnancy.ref_number)
                send_patient_message(db, pregnancy, patient_msg)

            sent += 1

    db.commit()
    return {"sent": sent, "skipped": skipped, "checked": len(pregnancies)}
