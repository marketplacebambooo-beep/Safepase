import logging

from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
AT_WHATSAPP_URL = "https://api.africastalking.com/version1/whatsapp/message"


def _contact(user) -> str:
    return user.phone or user.email


def _at_headers() -> dict:
    return {
        "apiKey": settings.at_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }


def _credentials_missing() -> bool:
    return not settings.at_api_key or not settings.at_username


def _dispatch_sms(phone: str, message: str) -> tuple[str, str | None]:
    phone = normalize_phone(phone) or phone

    if settings.sms_provider == "log":
        logger.info("SMS [%s]: %s", phone, message[:120])
        return "sent", None

    if settings.sms_provider != "africas_talking":
        logger.warning("Unsupported SMS provider: %s", settings.sms_provider)
        return "failed", None

    if _credentials_missing():
        logger.error("Africa's Talking credentials not configured (AT_USERNAME, AT_API_KEY)")
        return "failed", None

    try:
        payload = urlencode({
            "username": settings.at_username,
            "to": phone,
            "message": message,
            "from": settings.sms_sender_id,
        })
        resp = httpx.post(AT_SMS_URL, content=payload, headers=_at_headers(), timeout=20.0)
        data = resp.json() if resp.content else {}
        if resp.status_code == 201:
            recipients = data.get("SMSMessageData", {}).get("Recipients", [])
            if recipients:
                recipient = recipients[0]
                ref = recipient.get("messageId") or recipient.get("status")
                status_code = recipient.get("statusCode")
                if status_code in (101, 102):
                    return "sent", ref
                logger.error("SMS rejected for %s: %s", phone, recipient)
                return "failed", ref
        logger.error("SMS provider error (%s): %s", resp.status_code, data or resp.text)
        return "failed", None
    except Exception as exc:
        logger.exception("SMS send failed: %s", exc)
        return "failed", None


def _dispatch_whatsapp(phone: str, message: str) -> tuple[str, str | None]:
    phone = normalize_phone(phone) or phone

    if settings.whatsapp_provider == "log":
        logger.info("WhatsApp [%s]: %s", phone, message[:120])
        return "sent", None

    if settings.whatsapp_provider != "africas_talking":
        return "failed", None

    if _credentials_missing():
        logger.error("Africa's Talking credentials not configured for WhatsApp")
        return "failed", None

    try:
        payload = urlencode({
            "username": settings.at_username,
            "to": phone,
            "message": message,
            "from": settings.whatsapp_sender_id,
            "channel": "whatsapp",
        })
        resp = httpx.post(AT_WHATSAPP_URL, content=payload, headers=_at_headers(), timeout=20.0)
        if resp.status_code in (200, 201):
            data = resp.json() if resp.content else {}
            ref = data.get("id") or data.get("messageId")
            return "sent", ref
        logger.error("WhatsApp provider error (%s): %s", resp.status_code, resp.text)
        return "failed", None
    except Exception as exc:
        logger.exception("WhatsApp send failed: %s", exc)
        return "failed", None


def _record(
    db: Session,
    channel: str,
    recipient: str,
    message: str,
    status: str,
    provider_ref: str | None,
    pregnancy_id: int | None = None,
    referral_id: int | None = None,
):
    notification = Notification(
        pregnancy_id=pregnancy_id,
        referral_id=referral_id,
        channel=channel,
        recipient=recipient,
        message=message,
        status=status,
        provider_ref=provider_ref,
    )
    db.add(notification)
    db.flush()
    return notification


def send_sms(
    db: Session,
    recipient: str,
    message: str,
    pregnancy_id: int | None = None,
    referral_id: int | None = None,
):
    recipient = normalize_phone(recipient) or recipient
    status, provider_ref = _dispatch_sms(recipient, message)
    return _record(db, "sms", recipient, message, status, provider_ref, pregnancy_id, referral_id)


def send_whatsapp(
    db: Session,
    recipient: str,
    message: str,
    pregnancy_id: int | None = None,
    referral_id: int | None = None,
):
    recipient = normalize_phone(recipient) or recipient
    status, provider_ref = _dispatch_whatsapp(recipient, message)
    return _record(db, "whatsapp", recipient, message, status, provider_ref, pregnancy_id, referral_id)


def send_patient_message(
    db: Session,
    pregnancy,
    message: str,
    referral_id: int | None = None,
):
    """Send SMS always; also WhatsApp when patient opted in."""
    if not pregnancy.phone:
        return []
    results = [send_sms(db, pregnancy.phone, message, pregnancy.id, referral_id)]
    if getattr(pregnancy, "whatsapp_opt_in", True):
        results.append(send_whatsapp(db, pregnancy.phone, message, pregnancy.id, referral_id))
    return results


def retry_notification(db: Session, notification: Notification) -> Notification:
    if notification.channel == "whatsapp":
        status, provider_ref = _dispatch_whatsapp(notification.recipient, notification.message)
    elif notification.channel == "voice":
        from app.services.voice import dispatch_voice
        status, provider_ref = dispatch_voice(notification.recipient, notification.message, db)
    elif notification.channel == "airtime":
        from app.services.airtime import dispatch_airtime
        status, provider_ref = dispatch_airtime(notification.recipient)
    else:
        status, provider_ref = _dispatch_sms(notification.recipient, notification.message)
    notification.status = status
    notification.provider_ref = provider_ref
    db.commit()
    db.refresh(notification)
    return notification


def notify_user(db: Session, user, message: str, pregnancy_id: int | None = None, referral_id: int | None = None):
    return send_sms(db, _contact(user), message, pregnancy_id, referral_id)
