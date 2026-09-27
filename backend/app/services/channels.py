"""Live SMS/USSD/Voice/Airtime channel configuration and health checks."""

from app.config import settings


def _credentials_configured() -> bool:
    return bool(settings.at_username and settings.at_api_key)


def build_channel_status() -> dict:
    sms_live = settings.sms_provider == "africas_talking"
    whatsapp_live = settings.whatsapp_provider == "africas_talking"
    voice_live = settings.voice_enabled and settings.voice_provider == "africas_talking"
    airtime_live = settings.airtime_enabled and settings.airtime_provider == "africas_talking"
    creds = _credentials_configured()
    public_base = settings.public_api_url.rstrip("/") if settings.public_api_url else ""

    sms_ready = (not sms_live) or creds
    whatsapp_ready = (not whatsapp_live) or creds
    voice_ready = (not voice_live) or (creds and bool(settings.at_voice_phone))
    airtime_ready = (not airtime_live) or creds

    issues = []
    if sms_live and not creds:
        issues.append("SMS_PROVIDER=africas_talking but AT_USERNAME / AT_API_KEY are missing.")
    if whatsapp_live and not creds:
        issues.append("WHATSAPP_PROVIDER=africas_talking but AT_USERNAME / AT_API_KEY are missing.")
    if voice_live and not creds:
        issues.append("VOICE_PROVIDER=africas_talking but AT_USERNAME / AT_API_KEY are missing.")
    if voice_live and not settings.at_voice_phone:
        issues.append("AT_VOICE_PHONE is not set — register a Voice number in Africa's Talking.")
    if airtime_live and not creds:
        issues.append("AIRTIME_PROVIDER=africas_talking but AT_USERNAME / AT_API_KEY are missing.")
    if not public_base:
        issues.append("PUBLIC_API_URL is not set — register USSD and Voice callbacks after deployment.")

    return {
        "sms_provider": settings.sms_provider,
        "whatsapp_provider": settings.whatsapp_provider,
        "voice_provider": settings.voice_provider,
        "airtime_provider": settings.airtime_provider,
        "sms_ready": sms_ready,
        "whatsapp_ready": whatsapp_ready,
        "voice_ready": voice_ready,
        "airtime_ready": airtime_ready,
        "voice_enabled": settings.voice_enabled,
        "airtime_enabled": settings.airtime_enabled,
        "airtime_currency": settings.airtime_currency,
        "airtime_amount": settings.airtime_amount,
        "credentials_configured": creds,
        "at_username": settings.at_username or None,
        "sms_sender_id": settings.sms_sender_id,
        "whatsapp_sender_id": settings.whatsapp_sender_id,
        "voice_phone": settings.at_voice_phone or None,
        "ussd_callback_url": f"{public_base}/ussd/callback" if public_base else None,
        "voice_callback_url": f"{public_base}/voice/callback" if public_base else None,
        "ussd_service_code": settings.ussd_service_code or None,
        "issues": issues,
        "live_mode": sms_live or whatsapp_live or voice_live or airtime_live,
    }
