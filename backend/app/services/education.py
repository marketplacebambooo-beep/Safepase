import logging

from sqlalchemy.orm import Session

from app.i18n.messages import EDUCATION_WEEKS, EDUCATION
from app.models import EducationLog, Notification, Pregnancy
from app.services.ai_service import education_message_for_week
from app.services.notifications import send_patient_message

logger = logging.getLogger(__name__)


def _education_sent(db: Session, pregnancy_id: int, week: int, channel: str) -> bool:
    return (
        db.query(EducationLog)
        .filter(
            EducationLog.pregnancy_id == pregnancy_id,
            EducationLog.week_milestone == week,
            EducationLog.channel == channel,
        )
        .first()
        is not None
    )


def send_education_for_pregnancy(db: Session, pregnancy: Pregnancy, force_week: int | None = None) -> dict:
    """Send SMS + WhatsApp education for matching week milestone."""
    if not pregnancy.phone or pregnancy.status != "active":
        return {"sent": 0, "skipped": 0}

    weeks = [force_week] if force_week else EDUCATION_WEEKS
    sent = 0
    skipped = 0

    for week in weeks:
        if force_week is None and (pregnancy.weeks_pregnant or 0) < week:
            continue
        message = education_message_for_week(pregnancy, week)
        if not message:
            continue

        for channel in ("sms", "whatsapp"):
            if _education_sent(db, pregnancy.id, week, channel):
                skipped += 1
                continue
            if channel == "whatsapp" and not pregnancy.whatsapp_opt_in:
                continue

            from app.services.notifications import send_whatsapp, send_sms

            if channel == "sms":
                send_sms(db, pregnancy.phone, message, pregnancy.id)
            else:
                send_whatsapp(db, pregnancy.phone, message, pregnancy.id)

            db.add(EducationLog(pregnancy_id=pregnancy.id, week_milestone=week, channel=channel, message=message))
            sent += 1

    db.commit()
    return {"sent": sent, "skipped": skipped}


def run_weekly_education(db: Session) -> dict:
    """Batch job: send education to all active pregnancies at milestone weeks."""
    total_sent = 0
    total_skipped = 0
    pregnancies = db.query(Pregnancy).filter(Pregnancy.status == "active", Pregnancy.phone.isnot(None)).all()
    for pregnancy in pregnancies:
        result = send_education_for_pregnancy(db, pregnancy)
        total_sent += result["sent"]
        total_skipped += result["skipped"]
    logger.info("Education job: sent=%s skipped=%s", total_sent, total_skipped)
    return {"sent": total_sent, "skipped": total_skipped, "patients": len(pregnancies)}


def education_schedule(pregnancy: Pregnancy) -> list[dict]:
    lang = pregnancy.language or "en"
    schedule = []
    for week in EDUCATION_WEEKS:
        template = EDUCATION.get(week, {})
        schedule.append({
            "week": week,
            "message": (template.get(lang) or template.get("en", "")).format(ref=pregnancy.ref_number),
            "due": (pregnancy.weeks_pregnant or 0) >= week,
        })
    return schedule
