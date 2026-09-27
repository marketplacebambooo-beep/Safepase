import logging

from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import DangerSign, Facility, Pregnancy, Referral, User
from app.services.care_pathway import build_care_pathway, get_care_flags

logger = logging.getLogger(__name__)

ROLE_GUIDANCE = {
    "nurse": (
        "You assist clinic nurses using SafePass. Help with patient risk, danger signs, "
        "birth preparedness, referrals, and interpreting reports. Be concise and practical."
    ),
    "hospital": (
        "You assist hospital maternity staff using SafePass. Help with incoming referrals, "
        "pre-arrival context, urgency, and referral status workflow. Be concise and practical."
    ),
    "admin": (
        "You assist district administrators using SafePass. Help with facilities, users, CHWs, "
        "district analytics, and system overview. Be concise and practical."
    ),
}


def _facility_name(db: Session, facility_id: int | None) -> str:
    if not facility_id:
        return "District (all facilities)"
    f = db.get(Facility, facility_id)
    return f.name if f else "Unknown facility"


def build_role_context(db: Session, user: User) -> str:
    facility = _facility_name(db, user.facility_id)
    lines = [
        f"Staff member: {user.name}",
        f"Role: {user.role}",
        f"Facility: {facility}",
    ]

    if user.role == "nurse" and user.facility_id:
        pregnancies = db.query(Pregnancy).filter(
            Pregnancy.clinic_id == user.facility_id, Pregnancy.status == "active"
        ).all()
        high = [p for p in pregnancies if p.risk_level in ("red", "emergency")]
        lines += [
            f"Active pregnancies at clinic: {len(pregnancies)}",
            f"High risk / emergency: {len(high)}",
        ]
        if high:
            top = high[:5]
            lines.append("Priority patients: " + ", ".join(
                f"{p.first_name} {p.last_name} ({p.risk_level}, {p.weeks_pregnant}w, ref {p.ref_number})"
                for p in top
            ))

    elif user.role == "hospital" and user.facility_id:
        active_statuses = ("issued", "acknowledged", "in_transit", "arrived")
        referrals = db.query(Referral).filter(
            Referral.to_facility_id == user.facility_id,
            Referral.status.in_(active_statuses),
        ).order_by(Referral.issued_at.desc()).limit(10).all()
        emergencies = [r for r in referrals if r.urgency == "emergency"]
        lines += [
            f"Incoming active referrals: {len(referrals)}",
            f"Emergency referrals: {len(emergencies)}",
        ]
        if referrals:
            lines.append("Recent referrals: " + "; ".join(
                f"{r.ref_number} ({r.urgency}, {r.status})" for r in referrals[:5]
            ))

    elif user.role == "admin":
        facilities = db.query(Facility).count()
        users = db.query(User).count()
        active_preg = db.query(Pregnancy).filter(Pregnancy.status == "active").count()
        pending_refs = db.query(Referral).filter(
            Referral.status.in_(("issued", "acknowledged", "in_transit"))
        ).count()
        lines += [
            f"Facilities registered: {facilities}",
            f"System users: {users}",
            f"District active pregnancies: {active_preg}",
            f"Pending referrals network-wide: {pending_refs}",
        ]

    return "\n".join(lines)


def _rule_chat_reply(user: User, message: str, context: str) -> str:
    msg = message.lower()
    role = user.role

    if any(w in msg for w in ("hello", "hi", "mhoro", "sawubona", "help")):
        if role == "nurse":
            return (
                f"Hello {user.name}. I can help you review patients, danger signs, birth prep, "
                f"and referrals at your clinic. Ask in plain language — e.g. \"Who are my emergency cases?\""
            )
        if role == "hospital":
            return (
                f"Hello {user.name}. I can help with incoming referrals, urgency, and pre-arrival context. "
                f"Ask e.g. \"What emergency referrals are active?\""
            )
        return (
            f"Hello {user.name}. I can help with district overview, facilities, users, and analytics. "
            f"Ask e.g. \"How many active pregnancies are in the system?\""
        )

    if any(w in msg for w in ("risk", "emergency", "high", "danger", "patient", "referral", "pregnan", "active", "how many")):
        return (
            f"Based on your current SafePass data:\n{context}\n\n"
            f"Regarding your question: \"{message}\" — use the dashboard for live details. "
            f"Connect OpenAI API for richer natural-language answers."
        )

    return (
        f"I understand you asked: \"{message}\". Here is your current context:\n{context}\n\n"
        f"I am SafePass AI assistant for {user.role} staff. Ask about patients, referrals, "
        f"danger signs, birth prep, or district statistics. Configure OPENAI_API_KEY for full AI responses."
    )


def _call_openai_chat(system: str, history: list[dict], message: str) -> str | None:
    if not settings.openai_api_key:
        return None
    messages = [{"role": "system", "content": system}]
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})
    try:
        resp = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.4,
            },
            timeout=30.0,
        )
        data = resp.json()
        if resp.status_code == 200:
            return data["choices"][0]["message"]["content"].strip()
        logger.error("OpenAI chat error: %s", data)
    except Exception as exc:
        logger.exception("OpenAI chat failed: %s", exc)
    return None


def chat(
    db: Session,
    user: User,
    message: str,
    history: list[dict] | None = None,
) -> dict:
    history = history or []
    context = build_role_context(db, user)
    guidance = ROLE_GUIDANCE.get(user.role, ROLE_GUIDANCE["nurse"])
    system = (
        f"You are SafePass AI — a maternal health assistant for rural Zimbabwe. "
        f"{guidance} Never diagnose. Encourage clinical judgement. Max 4 sentences unless listing data.\n\n"
        f"Current user context:\n{context}"
    )
    ai_text = _call_openai_chat(system, history, message)
    content = ai_text or _rule_chat_reply(user, message, context)
    return {"content": content, "ai_powered": ai_text is not None}


def _recent_danger_count(db: Session, pregnancy_ids: list[int], days: int = 7) -> int:
    if not pregnancy_ids:
        return 0
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(DangerSign)
        .filter(DangerSign.pregnancy_id.in_(pregnancy_ids), DangerSign.reported_at >= since)
        .count()
    )


def build_dashboard_facts(db: Session, user: User) -> tuple[list[str], str]:
    """Return (highlight bullets, raw context block) for dashboard summary."""
    facility = _facility_name(db, user.facility_id)
    highlights: list[str] = []
    lines = [f"Staff: {user.name}", f"Role: {user.role}", f"Facility: {facility}"]

    if user.role == "nurse" and user.facility_id:
        pregnancies = (
            db.query(Pregnancy)
            .options(joinedload(Pregnancy.birth_prep))
            .filter(Pregnancy.clinic_id == user.facility_id, Pregnancy.status == "active")
            .all()
        )
        ids = [p.id for p in pregnancies]
        emergency = [p for p in pregnancies if p.risk_level == "emergency"]
        high = [p for p in pregnancies if p.risk_level in ("red", "emergency")]
        amber = [p for p in pregnancies if p.risk_level == "amber"]
        pending_refs = db.query(Referral).filter(
            Referral.from_facility_id == user.facility_id,
            Referral.status.in_(("issued", "acknowledged", "in_transit")),
        ).count()
        danger_week = _recent_danger_count(db, ids)
        low_prep = [
            p for p in pregnancies
            if p.birth_prep and (p.birth_prep.completed_pct or 0) < 50
        ]
        primigravida = [p for p in pregnancies if "first_pregnancy" in get_care_flags(p)]
        adolescents = [p for p in pregnancies if "adolescent" in get_care_flags(p)]
        twins = [p for p in pregnancies if "twins" in get_care_flags(p)]
        urgent_followups = []
        for p in pregnancies:
            pathway = build_care_pathway(db, p)
            if any(t["priority"] in ("high", "emergency") for t in pathway["follow_up_tasks"]):
                urgent_followups.append(p)

        lines += [
            f"Active pregnancies: {len(pregnancies)}",
            f"Emergency cases: {len(emergency)}",
            f"High risk (red+emergency): {len(high)}",
            f"Moderate risk (amber): {len(amber)}",
            f"Adolescent pregnancies (<18): {len(adolescents)}",
            f"First pregnancies (primigravida): {len(primigravida)}",
            f"Multiple gestation (twins+): {len(twins)}",
            f"Patients needing urgent follow-up: {len(urgent_followups)}",
            f"Pending outbound referrals: {pending_refs}",
            f"Danger signs reported (7 days): {danger_week}",
            f"Patients with birth prep below 50%: {len(low_prep)}",
        ]
        if emergency:
            highlights.append(
                f"{len(emergency)} emergency patient(s) need immediate attention: "
                + ", ".join(f"{p.first_name} {p.last_name}" for p in emergency[:3])
            )
        if urgent_followups:
            highlights.append(
                f"{len(urgent_followups)} patient(s) have overdue care-pathway follow-ups "
                f"(adolescent ANC, twins, post-term, or consent)."
            )
        if adolescents:
            highlights.append(f"{len(adolescents)} under-18 pregnancy case(s) — enhanced ANC monitoring active.")
        if primigravida:
            highlights.append(f"{len(primigravida)} first-pregnancy case(s) — ensure birth-prep counselling is complete.")
        if danger_week:
            highlights.append(f"{danger_week} danger sign report(s) in the last 7 days.")
        if pending_refs:
            highlights.append(f"{pending_refs} referral(s) awaiting hospital response.")
        if low_prep:
            highlights.append(f"{len(low_prep)} patient(s) have incomplete birth preparedness plans.")
        if not highlights:
            highlights.append("No critical alerts — continue routine monitoring and ANC.")

    elif user.role == "hospital" and user.facility_id:
        active_statuses = ("issued", "acknowledged", "in_transit", "arrived")
        referrals = (
            db.query(Referral)
            .filter(
                Referral.to_facility_id == user.facility_id,
                Referral.status.in_(active_statuses),
            )
            .order_by(Referral.issued_at.desc())
            .all()
        )
        emergencies = [r for r in referrals if r.urgency == "emergency"]
        in_transit = [r for r in referrals if r.status == "in_transit"]
        unacked = [r for r in referrals if r.status == "issued"]

        lines += [
            f"Active incoming referrals: {len(referrals)}",
            f"Emergency urgency: {len(emergencies)}",
            f"In transit now: {len(in_transit)}",
            f"Awaiting acknowledgment: {len(unacked)}",
        ]
        if emergencies:
            highlights.append(f"{len(emergencies)} emergency referral(s) require preparation.")
        if in_transit:
            highlights.append(f"{len(in_transit)} patient(s) currently in transit to your facility.")
        if unacked:
            highlights.append(f"{len(unacked)} referral(s) not yet acknowledged.")
        if not highlights:
            highlights.append("No active incoming referrals at this time.")

    elif user.role == "admin":
        facilities = db.query(Facility).count()
        users_count = db.query(User).count()
        active_preg = db.query(Pregnancy).filter(Pregnancy.status == "active").count()
        high_risk = db.query(Pregnancy).filter(
            Pregnancy.status == "active",
            Pregnancy.risk_level.in_(("red", "emergency", "amber")),
        ).count()
        pending_refs = db.query(Referral).filter(
            Referral.status.in_(("issued", "acknowledged", "in_transit"))
        ).count()
        emergencies = db.query(Pregnancy).filter(
            Pregnancy.status == "active", Pregnancy.risk_level == "emergency"
        ).count()

        lines += [
            f"Facilities: {facilities}",
            f"Users: {users_count}",
            f"Active pregnancies (district): {active_preg}",
            f"Elevated risk pregnancies: {high_risk}",
            f"Network-wide pending referrals: {pending_refs}",
            f"Emergency pregnancies: {emergencies}",
        ]
        if emergencies:
            highlights.append(f"{emergencies} emergency pregnancy case(s) across the district.")
        if pending_refs:
            highlights.append(f"{pending_refs} referral(s) in progress network-wide.")
        if not highlights:
            highlights.append("District operations are stable — no critical network alerts.")

    return highlights, "\n".join(lines)


def _rule_dashboard_summary(user: User, highlights: list[str], context: str) -> str:
    greeting = f"Good day, {user.name}."
    overview = " ".join(highlights[:3])
    actions = highlights[3:5] if len(highlights) > 3 else []
    action_lines = "\n".join(f"- {item}" for item in actions) if actions else "- Review the dashboard for live patient details."

    if user.role == "nurse":
        priority = "Review high-risk patients first, complete birth prep checklists, and follow up open referrals."
    elif user.role == "hospital":
        priority = "Acknowledge new referrals promptly and prepare for incoming emergency cases."
    else:
        priority = "Monitor referral flow and high-risk pregnancies across facilities."

    return (
        f"## Overview\n\n{greeting} Here is your briefing for today.\n\n"
        f"## Current status\n\n{overview}\n\n"
        f"## Key points\n\n{action_lines}\n\n"
        f"## Priority action\n\n{priority}"
    )


def generate_dashboard_summary(db: Session, user: User) -> dict:
    highlights, context = build_dashboard_facts(db, user)
    guidance = ROLE_GUIDANCE.get(user.role, ROLE_GUIDANCE["nurse"])
    system = (
        f"You are SafePass AI writing a dashboard briefing for a {user.role} in rural Zimbabwe. "
        f"{guidance} Never diagnose. Be direct and professional.\n\n"
        f"Format your response in markdown with exactly these sections:\n"
        f"## Overview\n"
        f"(1 short greeting paragraph)\n\n"
        f"## Current status\n"
        f"(2-3 sentences with specific numbers from the data)\n\n"
        f"## Key points\n"
        f"(- 3-5 bullet points with the most important facts)\n\n"
        f"## Priority action\n"
        f"(1 clear paragraph with the top recommended next step)\n\n"
        f"Use blank lines between sections. Do not wrap the whole response in one paragraph.\n\n"
        f"Data:\n{context}"
    )
    prompt = "Write today's dashboard briefing using the required markdown section headings."
    ai_text = _call_openai_chat(system, [], prompt)
    summary = ai_text or _rule_dashboard_summary(user, highlights, context)
    return {
        "summary": summary,
        "highlights": highlights,
        "ai_powered": ai_text is not None,
        "generated_at": datetime.utcnow(),
    }
