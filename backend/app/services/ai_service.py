import json
import logging

import httpx

from app.config import settings
from app.i18n.messages import DANGER_SIGN_LABELS, t
from app.models import Pregnancy

logger = logging.getLogger(__name__)

URGENCY_MAP = {
    "emergency": {"en": "EMERGENCY — immediate referral", "sn": "DZIKINISO — enda kuchipatara ikozvino", "nd": "ISIMO ESIPHUTHUMAYO — iya ngokushesha"},
    "red": {"en": "HIGH RISK — urgent clinic visit", "sn": "NGOZI YAKAKWIRA — enda kuchipatara nekukurumidza", "nd": "INGOZI EPHAKEME — iya ngokushesha esibhedlela"},
    "amber": {"en": "MODERATE — schedule clinic review", "sn": "PAKATI — ona kuchipatara munguva pfupi", "nd": "PHAKATHI — vakashe otholakala masinyane"},
    "green": {"en": "LOW RISK — continue routine care", "sn": "NGOZI YAKadera — ramba uchiteerera", "nd": "INGOZI EPHANSI — qhubeka nokunakekela okujwayelekile"},
}


def _lang(pregnancy: Pregnancy) -> str:
    return pregnancy.language if pregnancy.language in ("en", "sn", "nd") else "en"


def _sign_label(sign_type: str, lang: str) -> str:
    return DANGER_SIGN_LABELS.get(sign_type, {}).get(lang, sign_type)


def _rule_triage(pregnancy: Pregnancy, sign_type: str | None = None) -> str:
    lang = _lang(pregnancy)
    sign = _sign_label(sign_type or "other", lang)
    urgency = URGENCY_MAP.get(pregnancy.risk_level, URGENCY_MAP["green"]).get(lang, "")
    weeks = pregnancy.weeks_pregnant or "?"
    factors = []
    if pregnancy.previous_cs:
        factors.append("previous C-section" if lang == "en" else ("kare C-section" if lang == "sn" else "i-C-section yangaphambili"))
    if pregnancy.hypertension:
        factors.append("hypertension" if lang == "en" else ("BP yakakwira" if lang == "sn" else "i-blood pressure ephezulu"))
    factor_text = ", ".join(factors) if factors else ("none" if lang == "en" else ("hapana" if lang == "sn" else "akukho"))

    if lang == "sn":
        return (
            f"Triage brief: {pregnancy.first_name} ({weeks}svondo). Chiratidzo: {sign}. "
            f"Ngozi: {urgency}. Zvinhu: {factor_text}. Ref {pregnancy.ref_number}."
        )
    if lang == "nd":
        return (
            f"Triage brief: {pregnancy.first_name} ({weeks}amaviki). Upuhawu: {sign}. "
            f"Ingozi: {urgency}. Izinto: {factor_text}. Ref {pregnancy.ref_number}."
        )
    return (
        f"Triage brief: {pregnancy.first_name} ({weeks}wks). Sign: {sign}. "
        f"Urgency: {urgency}. Factors: {factor_text}. Ref {pregnancy.ref_number}."
    )


def _rule_referral_brief(pregnancy: Pregnancy, reason: str) -> str:
    lang = _lang(pregnancy)
    signs = ", ".join(s.sign_type for s in pregnancy.danger_signs[-3:]) or "none"
    if lang == "sn":
        return (
            f"Pre-arrival brief: {pregnancy.first_name} {pregnancy.last_name}, {pregnancy.weeks_pregnant}svondo, "
            f"ngoizi {pregnancy.risk_level}. Chikonzero: {reason}. Chiratidzo: {signs}. Ref {pregnancy.ref_number}."
        )
    if lang == "nd":
        return (
            f"Pre-arrival brief: {pregnancy.first_name} {pregnancy.last_name}, {pregnancy.weeks_pregnant}amaviki, "
            f"ingozi {pregnancy.risk_level}. Isizathu: {reason}. Upuhawu: {signs}. Ref {pregnancy.ref_number}."
        )
    return (
        f"Pre-arrival brief: {pregnancy.first_name} {pregnancy.last_name}, {pregnancy.weeks_pregnant}wks, "
        f"risk {pregnancy.risk_level}. Reason: {reason}. Recent signs: {signs}. Ref {pregnancy.ref_number}."
    )


def _call_openai(prompt: str) -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        resp = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a maternal health triage assistant for rural Zimbabwe. Be concise (max 2 sentences). Use plain language.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 150,
                "temperature": 0.3,
            },
            timeout=20.0,
        )
        data = resp.json()
        if resp.status_code == 200:
            return data["choices"][0]["message"]["content"].strip()
        logger.error("OpenAI error: %s", data)
    except Exception as exc:
        logger.exception("OpenAI call failed: %s", exc)
    return None


def generate_triage_brief(pregnancy: Pregnancy, sign_type: str | None = None) -> dict:
    lang = _lang(pregnancy)
    prompt = (
        f"Patient: {pregnancy.first_name}, {pregnancy.weeks_pregnant} weeks pregnant, "
        f"risk {pregnancy.risk_level}, danger sign: {sign_type or 'none'}, "
        f"previous CS: {pregnancy.previous_cs}, hypertension: {pregnancy.hypertension}. "
        f"Respond in {lang} language code (en/sn/nd). Give urgency and action."
    )
    ai_text = _call_openai(prompt)
    content = ai_text or _rule_triage(pregnancy, sign_type)
    return {"type": "triage", "language": lang, "content": content, "ai_powered": ai_text is not None}


def generate_referral_brief(pregnancy: Pregnancy, reason: str) -> dict:
    lang = _lang(pregnancy)
    prompt = (
        f"Hospital pre-arrival brief for referral. Patient {pregnancy.first_name} {pregnancy.last_name}, "
        f"{pregnancy.weeks_pregnant} weeks, risk {pregnancy.risk_level}. Reason: {reason}. "
        f"Recent danger signs: {[s.sign_type for s in pregnancy.danger_signs[-3:]]}. "
        f"Write 2 sentences in language {lang} for hospital staff."
    )
    ai_text = _call_openai(prompt)
    content = ai_text or _rule_referral_brief(pregnancy, reason)
    return {"type": "referral_brief", "language": lang, "content": content, "ai_powered": ai_text is not None}


def education_message_for_week(pregnancy: Pregnancy, week: int) -> str | None:
    from app.i18n.messages import EDUCATION

    template = EDUCATION.get(week)
    if not template:
        return None
    lang = _lang(pregnancy)
    return template.get(lang) or template.get("en", "").format(ref=pregnancy.ref_number)
