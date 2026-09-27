import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.i18n.messages import SUPPORTED_LANGUAGES, t
from app.models import AiInsight, BirthPrep, CHW, DangerSign, Pregnancy, UssdSession, User, Visit
from app.schemas import UssdRequest, UssdResponse
from app.services.ai_service import generate_triage_brief
from app.services.airtime import reward_chw
from app.services.dates import weeks_to_lmp_edd
from app.services.education import send_education_for_pregnancy
from app.services.notifications import notify_user, send_patient_message
from app.services.phone import normalize_phone, phone_variants
from app.services.risk_engine import calculate_risk
from app.services.follow_up_scheduler import notify_registration_pathway
from app.services.voice import HIGH_RISK, alert_staff_by_voice, emergency_script

router = APIRouter(prefix="/ussd", tags=["ussd"])


def _lang(session: dict) -> str:
    lang = session.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def _menu(session: dict) -> str:
    return t("ussd.menu", _lang(session))


def _language_menu(session: dict) -> str:
    return t("ussd.language_menu", _lang(session))


def _next_pregnancy_ref(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"SP-{year}-"
    last = (
        db.query(Pregnancy)
        .filter(Pregnancy.ref_number.like(f"{prefix}%"))
        .order_by(Pregnancy.id.desc())
        .first()
    )
    num = int(last.ref_number.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{num:04d}"


def _get_chw(db: Session, phone: str) -> CHW | None:
    variants = phone_variants(phone)
    if not variants:
        return None
    return db.query(CHW).filter(CHW.phone.in_(variants)).first()


def _session_get(db: Session, session_id: str) -> dict:
    row = db.get(UssdSession, session_id)
    if not row:
        return {}
    try:
        return json.loads(row.data)
    except json.JSONDecodeError:
        return {}


def _session_set(db: Session, session_id: str, data: dict):
    row = db.get(UssdSession, session_id)
    if row:
        row.data = json.dumps(data)
        row.updated_at = datetime.utcnow()
    else:
        db.add(UssdSession(session_id=session_id, data=json.dumps(data)))
    db.flush()


def _require_chw(db: Session, phone: str) -> CHW | UssdResponse:
    chw = _get_chw(db, phone)
    if not chw:
        return UssdResponse(
            response="END Phone not registered. Contact your clinic to register as a CHW.",
            end_session=True,
        )
    return chw


def _pregnancies_for_chw(db: Session, chw: CHW, limit: int = 8):
    return (
        db.query(Pregnancy)
        .filter(Pregnancy.chw_id == chw.id, Pregnancy.status == "active")
        .order_by(Pregnancy.created_at.desc())
        .limit(limit)
        .all()
    )


def _notify_clinic_nurses(db: Session, pregnancy: Pregnancy, message: str):
    nurses = db.query(User).filter(User.role == "nurse", User.facility_id == pregnancy.clinic_id).all()
    for nurse in nurses:
        notify_user(db, nurse, message, pregnancy.id)


def _report_danger_sign(db: Session, chw: CHW, pregnancy: Pregnancy, sign: str) -> tuple[str, str]:
    """Record danger sign, recalculate risk, notify clinic and patient. Returns (risk_level, end_message)."""
    triage = generate_triage_brief(pregnancy, sign)
    db.add(
        DangerSign(
            pregnancy_id=pregnancy.id,
            sign_type=sign,
            reporter_type="chw",
            reporter_id=chw.id,
            ai_brief=triage["content"] if triage else None,
        )
    )
    if triage:
        db.add(
            AiInsight(
                pregnancy_id=pregnancy.id,
                insight_type="triage",
                language=triage["language"],
                content=triage["content"],
                ai_powered=triage["ai_powered"],
            )
        )
    signs = [s.sign_type for s in pregnancy.danger_signs] + [sign]
    _, risk = calculate_risk(pregnancy, signs)
    pregnancy.risk_level = risk
    db.flush()

    alert = triage["content"] if triage else (
        f"ALERT: {pregnancy.first_name} {pregnancy.last_name} — {sign.replace('_', ' ')}. "
        f"Risk: {risk.upper()}. Ref {pregnancy.ref_number}."
    )
    _notify_clinic_nurses(db, pregnancy, alert)
    if pregnancy.phone:
        send_patient_message(db, pregnancy, t("danger_sign_patient", pregnancy.language, ref=pregnancy.ref_number))
    if risk in HIGH_RISK:
        nurses = db.query(User).filter(User.role == "nurse", User.facility_id == pregnancy.clinic_id).all()
        alert_staff_by_voice(db, nurses, emergency_script(pregnancy, sign=sign), pregnancy.id)
    reward = reward_chw(db, chw, "danger_sign", pregnancy)
    db.commit()
    message = f"END Alert sent! Ref {pregnancy.ref_number}. Clinic notified. Risk: {risk.upper()}."
    if reward and reward.status == "sent":
        message = f"{message} Airtime reward sent."
    return risk, message


def _safe_int(value: str, label: str) -> int | UssdResponse:
    try:
        return int(value)
    except (TypeError, ValueError):
        return UssdResponse(response=f"END Invalid {label}. Please try again.", end_session=True)


def _yes_no(value: str) -> bool:
    return value == "1"


@router.post("/callback")
async def ussd_callback_entry(request: Request, db: Session = Depends(get_db)):
    """Africa's Talking posts form data; JSON is accepted for automated tests."""
    content_type = request.headers.get("content-type", "")
    wants_json = "application/json" in content_type

    if wants_json:
        data = await request.json()
        body = UssdRequest(**data)
    else:
        form = await request.form()
        phone = str(form.get("phoneNumber") or form.get("phone") or "")
        text = str(form.get("text", ""))
        session_id = str(form.get("sessionId") or form.get("session_id") or phone)
        secret = request.headers.get("X-SafePass-Secret") or form.get("secret")
        body = UssdRequest(
            phone=phone,
            text=text,
            session_id=session_id,
            secret=str(secret) if secret else None,
        )

    result = _process_ussd(body, db)
    if wants_json:
        return result
    return PlainTextResponse(content=result.response, media_type="text/plain")


def _process_ussd(body: UssdRequest, db: Session) -> UssdResponse:
    if settings.ussd_callback_secret and body.secret != settings.ussd_callback_secret:
        raise HTTPException(status_code=401, detail="Invalid USSD callback secret")

    session_id = body.session_id or body.phone
    parts = body.text.split("*") if body.text else []
    step = len(parts)

    if not body.text:
        _session_set(db, session_id, {"lang": "en"})
        db.commit()
        return UssdResponse(response=_menu({"lang": "en"}))

    session = _session_get(db, session_id)
    choice = parts[0]

    if choice == "5":
        if step == 1:
            return UssdResponse(response=_language_menu(session))
        if step == 2:
            lang_map = {"1": "en", "2": "sn", "3": "nd"}
            lang = lang_map.get(parts[1], "en")
            session["lang"] = lang
            _session_set(db, session_id, session)
            db.commit()
            return UssdResponse(response=t("ussd.language_set", lang), end_session=True)

    if choice == "1":
        chw = _require_chw(db, body.phone)
        if isinstance(chw, UssdResponse):
            return chw
        prompts = {
            1: "CON Enter patient first name:",
            2: "CON Enter patient last name:",
            3: "CON Enter patient age:",
            4: "CON Enter weeks pregnant:",
            5: "CON Enter village name:",
            6: "CON Previous C-section?\n1. Yes\n2. No",
            7: "CON Hypertension?\n1. Yes\n2. No",
            8: "CON Previous live births? (0=first pregnancy):",
            9: "CON Twins/multiple pregnancy?\n1. Yes\n2. No",
            10: "CON Enter patient phone (or 0 to skip):",
        }
        if step in prompts:
            return UssdResponse(response=prompts[step])
        if step == 11:
            first_name, last_name, age_s, weeks_s, village, cs_s, htn_s, parity_s, twins_s, phone_raw = (
                parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7], parts[8], parts[9], parts[10]
            )
            age = _safe_int(age_s, "age")
            if isinstance(age, UssdResponse):
                return age
            weeks = _safe_int(weeks_s, "weeks")
            if isinstance(weeks, UssdResponse):
                return weeks
            parity = _safe_int(parity_s, "parity")
            if isinstance(parity, UssdResponse):
                return parity
            if parity < 0 or parity > 15:
                return UssdResponse(response="END Invalid parity. Try again.", end_session=True)
            if cs_s not in ("1", "2") or htn_s not in ("1", "2") or twins_s not in ("1", "2"):
                return UssdResponse(response="END Invalid risk answer. Try again.", end_session=True)
            patient_phone = None if phone_raw == "0" else normalize_phone(phone_raw)
            if patient_phone:
                existing = db.query(Pregnancy).filter(Pregnancy.phone == patient_phone, Pregnancy.status == "active").first()
                if existing:
                    return UssdResponse(response=f"END Active patient exists: {existing.ref_number}", end_session=True)
            lmp, edd = weeks_to_lmp_edd(weeks)
            ref = _next_pregnancy_ref(db)
            twins = _yes_no(twins_s)
            gravida = max(parity + 1, 1)
            pregnancy = Pregnancy(
                ref_number=ref,
                first_name=first_name.title(),
                last_name=last_name.title(),
                age=age,
                weeks_pregnant=weeks,
                lmp_date=lmp,
                edd=edd,
                village=village.title(),
                phone=patient_phone,
                chw_id=chw.id,
                clinic_id=chw.facility_id,
                previous_cs=_yes_no(cs_s),
                hypertension=_yes_no(htn_s),
                multiple_gestation=twins,
                fetal_count=2 if twins else 1,
                gravida=gravida,
                parity=parity,
                guardian_consent_recorded=age >= 18,
                consent_recorded=True,
                language=_lang(session),
                whatsapp_opt_in=True,
            )
            _, risk = calculate_risk(pregnancy)
            pregnancy.risk_level = risk
            db.add(pregnancy)
            db.flush()
            db.add(BirthPrep(pregnancy_id=pregnancy.id))
            if patient_phone:
                send_patient_message(db, pregnancy, t("registered", pregnancy.language, ref=ref))
                if twins:
                    send_patient_message(db, pregnancy, t("followup_twins", pregnancy.language, ref=ref))
                if parity == 0:
                    send_patient_message(db, pregnancy, t("followup_first_pregnancy", pregnancy.language, ref=ref))
            _notify_clinic_nurses(db, pregnancy, f"New registration: {pregnancy.first_name} {pregnancy.last_name}. Ref {ref}.")
            notify_registration_pathway(db, pregnancy)
            reward = reward_chw(db, chw, "register", pregnancy)
            db.commit()
            send_education_for_pregnancy(db, pregnancy)
            suffix = " Airtime reward sent." if reward and reward.status == "sent" else ""
            return UssdResponse(response=f"END Registered! Ref: {ref}. Nurse will follow up.{suffix}", end_session=True)

    if choice == "2":
        chw = _require_chw(db, body.phone)
        if isinstance(chw, UssdResponse):
            return chw
        if step == 1:
            pregnancies = _pregnancies_for_chw(db, chw)
            if not pregnancies:
                return UssdResponse(response="END No active pregnancies found.", end_session=True)
            lines = [f"{i+1}. {p.first_name} {p.last_name} ({p.weeks_pregnant}wks)" for i, p in enumerate(pregnancies)]
            _session_set(db, session_id, {"list": [p.id for p in pregnancies]})
            db.commit()
            return UssdResponse(response="CON Select patient for check-in:\n" + "\n".join(lines))
        if step == 2:
            session = _session_get(db, session_id)
            preg_ids = session.get("list", [])
            idx_result = _safe_int(parts[1], "selection")
            if isinstance(idx_result, UssdResponse):
                return idx_result
            idx = idx_result - 1
            if idx < 0 or idx >= len(preg_ids):
                return UssdResponse(response="END Invalid selection.", end_session=True)
            pregnancy = db.get(Pregnancy, preg_ids[idx])
            if not pregnancy:
                return UssdResponse(response="END Patient not found.", end_session=True)
            db.add(
                Visit(
                    pregnancy_id=pregnancy.id,
                    facility_id=pregnancy.clinic_id,
                    chw_id=chw.id,
                    visit_type="check_in",
                    notes=f"USSD check-in at {pregnancy.weeks_pregnant} weeks",
                )
            )
            _notify_clinic_nurses(
                db,
                pregnancy,
                f"Check-in: {pregnancy.first_name} {pregnancy.last_name} at {pregnancy.weeks_pregnant} weeks. Ref {pregnancy.ref_number}.",
            )
            db.commit()
            return UssdResponse(
                response=f"END Check-in recorded for {pregnancy.first_name}. Ref {pregnancy.ref_number}.",
                end_session=True,
            )

    if choice == "3":
        chw = _require_chw(db, body.phone)
        if isinstance(chw, UssdResponse):
            return chw
        if step == 1:
            pregnancies = _pregnancies_for_chw(db, chw)
            if not pregnancies:
                return UssdResponse(response="END No active pregnancies found.", end_session=True)
            lines = [f"{i+1}. {p.first_name} {p.last_name} ({p.weeks_pregnant}wks)" for i, p in enumerate(pregnancies)]
            _session_set(db, session_id, {"list": [p.id for p in pregnancies]})
            db.commit()
            return UssdResponse(response="CON Select pregnancy:\n" + "\n".join(lines))
        if step == 2:
            return UssdResponse(
                response="CON Select danger sign:\n1. Bleeding\n2. Severe headache\n3. Swelling\n4. Reduced movement\n5. Other"
            )
        if step == 3:
            session = _session_get(db, session_id)
            preg_ids = session.get("list", [])
            idx_result = _safe_int(parts[1], "selection")
            if isinstance(idx_result, UssdResponse):
                return idx_result
            idx = idx_result - 1
            sign_map = {"1": "bleeding", "2": "severe_headache", "3": "swelling", "4": "reduced_movement", "5": "other"}
            sign = sign_map.get(parts[2], "other")
            if idx < 0 or idx >= len(preg_ids):
                return UssdResponse(response="END Invalid selection.", end_session=True)
            pregnancy = db.get(Pregnancy, preg_ids[idx])
            if not pregnancy:
                return UssdResponse(response="END Pregnancy not found.", end_session=True)

            _, end_message = _report_danger_sign(db, chw, pregnancy, sign)
            return UssdResponse(response=end_message, end_session=True)

    if choice == "4":
        chw = _require_chw(db, body.phone)
        if isinstance(chw, UssdResponse):
            return chw
        pregnancies = _pregnancies_for_chw(db, chw, limit=5)
        if not pregnancies:
            return UssdResponse(response="END No active pregnancies.", end_session=True)
        lines = [f"{p.ref_number}: {p.first_name} {p.last_name}, {p.weeks_pregnant}wks, {p.risk_level}" for p in pregnancies]
        return UssdResponse(response="END Your pregnancies:\n" + "\n".join(lines), end_session=True)

    return UssdResponse(response="END Invalid option. Please try again.", end_session=True)


@router.post("/callback/at")
async def ussd_callback_africas_talking_alias(request: Request, db: Session = Depends(get_db)):
    """Backward-compatible alias — same handler as /ussd/callback."""
    return await ussd_callback_entry(request, db)
