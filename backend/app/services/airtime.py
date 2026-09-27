import json
import logging
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AirtimeReward, CHW
from app.services.notifications import _record, send_sms
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

AT_AIRTIME_URL = "https://api.africastalking.com/version1/airtime/send"


def _at_headers() -> dict:
    return {
        "apiKey": settings.at_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }


def _credentials_missing() -> bool:
    return not settings.at_api_key or not settings.at_username


def already_rewarded(db: Session, chw_id: int, reason: str, pregnancy_id: int | None) -> bool:
    query = db.query(AirtimeReward).filter(
        AirtimeReward.chw_id == chw_id,
        AirtimeReward.reason == reason,
        AirtimeReward.status == "sent",
    )
    if pregnancy_id is not None:
        query = query.filter(AirtimeReward.pregnancy_id == pregnancy_id)
    return query.first() is not None


def dispatch_airtime(phone: str) -> tuple[str, str | None]:
    phone = normalize_phone(phone) or phone

    if not settings.airtime_enabled or settings.airtime_provider == "log":
        logger.info("Airtime [%s]: %s %s", phone, settings.airtime_currency, settings.airtime_amount)
        return "sent", None

    if settings.airtime_provider != "africas_talking":
        logger.warning("Unsupported airtime provider: %s", settings.airtime_provider)
        return "failed", None

    if _credentials_missing():
        logger.error("Africa's Talking airtime is missing AT_USERNAME or AT_API_KEY")
        return "failed", None

    recipients = json.dumps([{
        "phoneNumber": phone,
        "currencyCode": settings.airtime_currency,
        "amount": str(settings.airtime_amount),
    }])
    try:
        payload = urlencode({
            "username": settings.at_username,
            "recipients": recipients,
        })
        resp = httpx.post(AT_AIRTIME_URL, content=payload, headers=_at_headers(), timeout=20.0)
        data = resp.json() if resp.content else {}
        responses = data.get("responses") or []
        if resp.status_code in (200, 201) and (data.get("numSent", 0) or responses):
            entry = responses[0] if responses else {}
            ref = entry.get("requestId") or entry.get("status")
            status = (entry.get("status") or "Sent").lower()
            if status in ("sent", "success") or data.get("numSent", 0):
                return "sent", ref
            logger.error("Airtime rejected for %s: %s", phone, entry)
            return "failed", ref
        logger.error("Airtime provider error (%s): %s", resp.status_code, data or resp.text)
        return "failed", None
    except Exception as exc:
        logger.exception("Airtime send failed: %s", exc)
        return "failed", None


def reward_chw(
    db: Session,
    chw: CHW,
    reason: str,
    pregnancy=None,
) -> AirtimeReward | None:
    if not settings.airtime_enabled or not chw or not chw.phone:
        return None
    pregnancy_id = pregnancy.id if pregnancy is not None else None
    if already_rewarded(db, chw.id, reason, pregnancy_id):
        return None

    phone = normalize_phone(chw.phone) or chw.phone
    status, provider_ref = dispatch_airtime(phone)
    label = "registering a patient" if reason == "register" else "reporting a danger sign"
    message = (
        f"SafePass: {settings.airtime_currency} {settings.airtime_amount} airtime "
        f"for {label}."
    )
    reward = AirtimeReward(
        chw_id=chw.id,
        pregnancy_id=pregnancy_id,
        reason=reason,
        currency=settings.airtime_currency,
        amount=str(settings.airtime_amount),
        status=status,
        provider_ref=provider_ref,
    )
    db.add(reward)
    db.flush()
    _record(db, "airtime", phone, message, status, provider_ref, pregnancy_id)
    if status == "sent":
        send_sms(db, phone, message, pregnancy_id)
    return reward
