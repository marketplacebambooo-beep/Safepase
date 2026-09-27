import logging
import uuid
from urllib.parse import urlencode
from xml.sax.saxutils import escape

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, VoicePrompt
from app.services.notifications import _record
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

AT_VOICE_URL = "https://voice.africastalking.com/call"
HIGH_RISK = {"red", "emergency"}


def emergency_script(pregnancy, sign: str | None = None, reason: str | None = None) -> str:
    name = f"{pregnancy.first_name} {pregnancy.last_name}"
    parts = [f"SafePass emergency. Patient {name}. Reference {pregnancy.ref_number}."]
    if sign:
        parts.append(f"Danger sign: {sign.replace('_', ' ')}.")
    if reason:
        parts.append(f"Referral reason: {reason}.")
    parts.append(f"Risk {pregnancy.risk_level}. Open the SafePass dashboard now.")
    return " ".join(parts)


def _at_headers() -> dict:
    return {
        "apiKey": settings.at_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }


def _credentials_missing() -> bool:
    return not settings.at_api_key or not settings.at_username or not settings.at_voice_phone


def dispatch_voice(phone: str, message: str, db: Session | None = None) -> tuple[str, str | None]:
    phone = normalize_phone(phone) or phone

    if not settings.voice_enabled or settings.voice_provider == "log":
        logger.info("Voice [%s]: %s", phone, message[:120])
        return "sent", None

    if settings.voice_provider != "africas_talking":
        logger.warning("Unsupported voice provider: %s", settings.voice_provider)
        return "failed", None

    if _credentials_missing():
        logger.error("Africa's Talking voice is missing AT_USERNAME, AT_API_KEY, or AT_VOICE_PHONE")
        return "failed", None

    request_id = uuid.uuid4().hex
    if db is not None:
        db.add(VoicePrompt(request_id=request_id, recipient=phone, message=message))
        db.flush()

    try:
        payload = urlencode({
            "username": settings.at_username,
            "from": settings.at_voice_phone,
            "to": phone,
            "clientRequestId": request_id,
        })
        resp = httpx.post(AT_VOICE_URL, content=payload, headers=_at_headers(), timeout=20.0)
        data = resp.json() if resp.content else {}
        entries = data.get("entries") or []
        if resp.status_code in (200, 201) and entries:
            entry = entries[0]
            session_id = entry.get("sessionId")
            status = (entry.get("status") or "").lower()
            if db is not None and session_id:
                prompt = db.query(VoicePrompt).filter(VoicePrompt.request_id == request_id).first()
                if prompt:
                    prompt.session_id = session_id
                    db.flush()
            if status in ("queued", "success"):
                return "sent", session_id or request_id
            logger.error("Voice rejected for %s: %s", phone, entry)
            return "failed", session_id or request_id
        logger.error("Voice provider error (%s): %s", resp.status_code, data or resp.text)
        return "failed", request_id
    except Exception as exc:
        logger.exception("Voice call failed: %s", exc)
        return "failed", request_id


def lookup_prompt(db: Session, session_id: str = "", request_id: str = "", recipient: str = "") -> VoicePrompt | None:
    if request_id:
        prompt = db.query(VoicePrompt).filter(VoicePrompt.request_id == request_id).first()
        if prompt:
            return prompt
    if session_id:
        prompt = db.query(VoicePrompt).filter(VoicePrompt.session_id == session_id).first()
        if prompt:
            return prompt
    if recipient:
        variants = {recipient, normalize_phone(recipient) or recipient}
        return (
            db.query(VoicePrompt)
            .filter(VoicePrompt.recipient.in_([v for v in variants if v]))
            .order_by(VoicePrompt.created_at.desc())
            .first()
        )
    return None


def render_say_xml(message: str) -> str:
    spoken = escape(message or "SafePass emergency alert. Please check your dashboard.")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say voice="en-US-Standard-C" playBeep="false">{spoken}</Say></Response>'
    )


def alert_staff_by_voice(
    db: Session,
    users: list[User],
    message: str,
    pregnancy_id: int | None = None,
    referral_id: int | None = None,
):
    if not settings.voice_enabled:
        return []
    seen: set[str] = set()
    results = []
    for user in users:
        phone = normalize_phone(user.phone) if user.phone else None
        if not phone or phone in seen:
            continue
        seen.add(phone)
        status, provider_ref = dispatch_voice(phone, message, db)
        results.append(_record(db, "voice", phone, message, status, provider_ref, pregnancy_id, referral_id))
    return results
