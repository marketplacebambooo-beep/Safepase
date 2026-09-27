from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    AiChatMessage,
    AiChatSession,
    AiInsight,
    AuditLog,
    BirthPrep,
    CHW,
    DangerSign,
    Facility,
    Notification,
    Pregnancy,
    Referral,
    ReferralStatus,
    User,
    Visit,
)
from app.schemas import (
    AiChatMessageOut,
    AiChatRequest,
    AiChatResponse,
    AiChatSessionOut,
    AiAttachResponse,
    AiTranscribeResponse,
    AiDashboardSummaryOut,
    AiInsightOut,
    AnalyticsSummary,
    AuditLogOut,
    BirthPrepOut,
    BirthPrepUpdate,
    CHWOut,
    DangerSignCreate,
    DistrictAnalytics,
    EducationItemOut,
    FacilityOut,
    NotificationOut,
    PregnancyCareUpdate,
    PregnancyCreate,
    PregnancyDetailOut,
    PregnancyOut,
    PregnancyStatusUpdate,
    CarePathwayOut,
    AncCalendarEntryOut,
    ComplianceReportOut,
    ReferralCreate,
    ReferralOut,
    VisitOut,
)
from app.config import settings
from app.i18n.messages import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, t
from app.services.ai_service import generate_referral_brief, generate_triage_brief
from app.services.voice import HIGH_RISK, alert_staff_by_voice, emergency_script
from app.services.ai_chat_service import chat as ai_chat
from app.services.ai_chat_service import generate_dashboard_summary
from app.services.ai_media_service import extract_file_content, transcribe_audio
from app.services.audit import log_action
from app.services.channels import build_channel_status
from app.services.dates import weeks_to_lmp_edd
from app.services.education import education_schedule, send_education_for_pregnancy
from app.services.notifications import notify_user, retry_notification, send_patient_message, send_sms
from app.services.permissions import (
    assert_clinic_nurse,
    assert_hospital_referral,
    assert_pregnancy_access,
    require_roles,
)
from app.services.phone import normalize_phone
from app.services.referrals import assert_valid_transition
from app.services.risk_engine import calculate_risk
from app.services.care_pathway import build_care_pathway, build_compliance_report, get_clinic_anc_calendar
from app.services.follow_up_scheduler import notify_registration_pathway

router = APIRouter(prefix="/api", tags=["api"])

STATUS_SMS = {
    ReferralStatus.ACKNOWLEDGED.value: "Hospital has acknowledged your referral and is preparing.",
    ReferralStatus.IN_TRANSIT.value: "You are marked in transit. Proceed to hospital.",
    ReferralStatus.ARRIVED.value: "You have arrived at hospital. Care team notified.",
    ReferralStatus.COMPLETED.value: "Referral completed. Thank you for using SafePass.",
    ReferralStatus.CANCELLED.value: "Your referral has been cancelled. Contact your clinic.",
    ReferralStatus.NO_SHOW.value: "You were marked as no-show. Please contact your clinic urgently.",
}


def _session_title_from_message(message: str) -> str:
    clean = message.strip().replace("\n", " ")
    if not clean:
        return "New chat"
    return clean[:48] + ("..." if len(clean) > 48 else "")


def _migrate_orphan_messages(db: Session, user: User) -> None:
    orphan_count = db.query(AiChatMessage).filter(
        AiChatMessage.user_id == user.id,
        AiChatMessage.session_id.is_(None),
    ).count()
    if not orphan_count:
        return
    session = AiChatSession(user_id=user.id, title="Previous conversation")
    db.add(session)
    db.flush()
    db.query(AiChatMessage).filter(
        AiChatMessage.user_id == user.id,
        AiChatMessage.session_id.is_(None),
    ).update({AiChatMessage.session_id: session.id}, synchronize_session=False)
    session.updated_at = datetime.utcnow()


def _get_or_create_session(db: Session, user: User, session_id: int | None) -> AiChatSession:
    if session_id:
        session = db.query(AiChatSession).filter(
            AiChatSession.id == session_id,
            AiChatSession.user_id == user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return session
    session = AiChatSession(user_id=user.id, title="New chat")
    db.add(session)
    db.flush()
    return session


def _birth_prep_out(bp: BirthPrep) -> BirthPrepOut:
    return BirthPrepOut(
        facility_identified=bp.facility_identified,
        escort_identified=bp.escort_identified,
        escort_phone=bp.escort_phone,
        transport_plan=bp.transport_plan,
        emergency_savings=bp.emergency_savings,
        danger_education_done=bp.danger_education_done,
        bag_prepared=bp.bag_prepared,
        completed_pct=bp.completed_pct,
    )


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


def _next_ref_number(db: Session, prefix: str) -> str:
    year = datetime.utcnow().year
    full_prefix = f"{prefix}-{year}-"
    last = (
        db.query(Referral)
        .filter(Referral.ref_number.like(f"{full_prefix}%"))
        .order_by(Referral.id.desc())
        .first()
    )
    num = int(last.ref_number.split("-")[-1]) + 1 if last else 1
    return f"{full_prefix}{num:04d}"


def _referral_out(referral: Referral, db: Session) -> ReferralOut:
    pregnancy = db.get(Pregnancy, referral.pregnancy_id)
    from_f = db.get(Facility, referral.from_facility_id)
    to_f = db.get(Facility, referral.to_facility_id)
    return ReferralOut(
        id=referral.id,
        ref_number=referral.ref_number,
        pregnancy_id=referral.pregnancy_id,
        from_facility_id=referral.from_facility_id,
        to_facility_id=referral.to_facility_id,
        urgency=referral.urgency,
        reason=referral.reason,
        status=referral.status,
        issued_at=referral.issued_at,
        acknowledged_at=referral.acknowledged_at,
        departed_at=referral.departed_at,
        arrived_at=referral.arrived_at,
        completed_at=referral.completed_at,
        patient_name=f"{pregnancy.first_name} {pregnancy.last_name}" if pregnancy else None,
        patient_weeks=pregnancy.weeks_pregnant if pregnancy else None,
        from_facility_name=from_f.name if from_f else None,
        to_facility_name=to_f.name if to_f else None,
    )


def _scoped_pregnancy_query(db: Session, user: User):
    query = db.query(Pregnancy)
    if user.role == "nurse" and user.facility_id:
        return query.filter(Pregnancy.clinic_id == user.facility_id)
    if user.role == "hospital" and user.facility_id:
        preg_ids = (
            db.query(Referral.pregnancy_id)
            .filter(Referral.to_facility_id == user.facility_id)
            .distinct()
            .subquery()
        )
        return query.filter(Pregnancy.id.in_(preg_ids))
    return query


@router.get("/facilities", response_model=list[FacilityOut])
def list_facilities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Facility).order_by(Facility.name).all()


@router.get("/chws", response_model=list[CHWOut])
def list_chws(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(CHW)
    if user.role == "nurse" and user.facility_id:
        query = query.filter(CHW.facility_id == user.facility_id)
    return query.order_by(CHW.name).all()


@router.get("/pregnancies", response_model=list[PregnancyOut])
def list_pregnancies(
    risk: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "hospital":
        raise HTTPException(status_code=403, detail="Use referrals to access patients")
    query = _scoped_pregnancy_query(db, user).options(joinedload(Pregnancy.danger_signs))
    if risk and risk != "all":
        query = query.filter(Pregnancy.risk_level == risk)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Pregnancy.first_name.ilike(like))
            | (Pregnancy.last_name.ilike(like))
            | (Pregnancy.ref_number.ilike(like))
            | (Pregnancy.village.ilike(like))
        )
    return query.order_by(Pregnancy.created_at.desc()).all()


@router.post("/pregnancies", response_model=PregnancyOut)
def create_pregnancy(
    body: PregnancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "nurse" or not user.facility_id:
        raise HTTPException(status_code=403, detail="Only clinic nurses can register patients")

    if body.chw_id:
        chw = db.get(CHW, body.chw_id)
        if not chw or chw.facility_id != user.facility_id:
            raise HTTPException(status_code=400, detail="Invalid CHW for this clinic")

    phone = normalize_phone(body.phone)
    if phone:
        existing = db.query(Pregnancy).filter(Pregnancy.phone == phone, Pregnancy.status == "active").first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Active patient with this phone exists: {existing.ref_number}")

    lmp, edd = weeks_to_lmp_edd(body.weeks_pregnant)
    pregnancy = Pregnancy(
        ref_number=_next_pregnancy_ref(db),
        first_name=body.first_name.title(),
        last_name=body.last_name.title(),
        age=body.age,
        weeks_pregnant=body.weeks_pregnant,
        lmp_date=lmp,
        edd=edd,
        village=body.village.title(),
        phone=phone,
        chw_id=body.chw_id,
        clinic_id=user.facility_id,
        previous_cs=body.previous_cs,
        hypertension=body.hypertension,
        multiple_gestation=body.multiple_gestation,
        fetal_count=max(1, body.fetal_count),
        guardian_consent_recorded=body.guardian_consent_recorded or body.age >= 18,
        gravida=max(body.gravida, body.parity + 1),
        parity=body.parity,
        consent_recorded=body.consent_recorded,
        language=body.language if body.language in SUPPORTED_LANGUAGES else "en",
        whatsapp_opt_in=body.whatsapp_opt_in,
    )
    _, risk = calculate_risk(pregnancy)
    pregnancy.risk_level = risk
    db.add(pregnancy)
    db.flush()
    db.add(BirthPrep(pregnancy_id=pregnancy.id))

    if pregnancy.phone:
        msg = t("registered", pregnancy.language, ref=pregnancy.ref_number)
        send_patient_message(db, pregnancy, msg)
        if pregnancy.multiple_gestation:
            send_patient_message(db, pregnancy, t("followup_twins", pregnancy.language, ref=pregnancy.ref_number))
        if (pregnancy.parity or 0) == 0:
            send_patient_message(db, pregnancy, t("followup_first_pregnancy", pregnancy.language, ref=pregnancy.ref_number))

    notify_registration_pathway(db, pregnancy)

    log_action(db, user, "create", "pregnancy", pregnancy.id, pregnancy.ref_number)
    db.commit()
    db.refresh(pregnancy)
    send_education_for_pregnancy(db, pregnancy)
    return pregnancy


@router.get("/pregnancies/{pregnancy_id}", response_model=PregnancyDetailOut)
def get_pregnancy(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = (
        db.query(Pregnancy)
        .options(
            joinedload(Pregnancy.danger_signs),
            joinedload(Pregnancy.birth_prep),
            joinedload(Pregnancy.referrals),
        )
        .filter(Pregnancy.id == pregnancy_id)
        .first()
    )
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)

    data = PregnancyDetailOut.model_validate(pregnancy)
    if pregnancy.birth_prep:
        data.birth_prep = _birth_prep_out(pregnancy.birth_prep)
    data.care_pathway = CarePathwayOut.model_validate(build_care_pathway(db, pregnancy))
    data.referrals = [_referral_out(r, db) for r in sorted(pregnancy.referrals, key=lambda x: x.issued_at, reverse=True)]
    return data


@router.patch("/pregnancies/{pregnancy_id}/status", response_model=PregnancyOut)
def update_pregnancy_status(
    pregnancy_id: int,
    body: PregnancyStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_clinic_nurse(user, pregnancy)
    if body.status not in ("active", "discharged", "lost_to_followup"):
        raise HTTPException(status_code=400, detail="Invalid status")
    pregnancy.status = body.status
    log_action(db, user, "status_change", "pregnancy", pregnancy.id, body.status)
    db.commit()
    db.refresh(pregnancy)
    return pregnancy


@router.patch("/pregnancies/{pregnancy_id}/care", response_model=PregnancyOut)
def update_pregnancy_care(
    pregnancy_id: int,
    body: PregnancyCareUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_clinic_nurse(user, pregnancy)

    if body.guardian_consent_recorded is not None:
        pregnancy.guardian_consent_recorded = body.guardian_consent_recorded
    if body.multiple_gestation is not None:
        pregnancy.multiple_gestation = body.multiple_gestation
        if body.multiple_gestation and (body.fetal_count is None or body.fetal_count < 2):
            pregnancy.fetal_count = 2
    if body.fetal_count is not None:
        pregnancy.fetal_count = max(1, body.fetal_count)
    if body.gravida is not None:
        pregnancy.gravida = body.gravida
    if body.parity is not None:
        pregnancy.parity = body.parity
        if body.gravida is None:
            pregnancy.gravida = max(pregnancy.gravida or 1, body.parity + 1)

    _, risk = calculate_risk(pregnancy)
    pregnancy.risk_level = risk
    log_action(db, user, "update", "pregnancy_care", pregnancy.id, pregnancy.ref_number)
    db.commit()
    db.refresh(pregnancy)
    return pregnancy


@router.get("/pregnancies/{pregnancy_id}/care-pathway", response_model=CarePathwayOut)
def get_care_pathway(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = (
        db.query(Pregnancy)
        .options(joinedload(Pregnancy.birth_prep))
        .filter(Pregnancy.id == pregnancy_id)
        .first()
    )
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)
    return CarePathwayOut.model_validate(build_care_pathway(db, pregnancy))


@router.post("/pregnancies/{pregnancy_id}/danger-signs", response_model=PregnancyOut)
def add_danger_sign(
    pregnancy_id: int,
    body: DangerSignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_clinic_nurse(user, pregnancy)

    triage = generate_triage_brief(pregnancy, body.sign_type)
    sign = DangerSign(
        pregnancy_id=pregnancy.id,
        sign_type=body.sign_type,
        description=body.description,
        reporter_type="nurse",
        reporter_id=user.id,
        ai_brief=triage["content"] if triage else None,
    )
    db.add(sign)
    signs = [s.sign_type for s in pregnancy.danger_signs] + [body.sign_type]
    _, risk = calculate_risk(pregnancy, signs)
    pregnancy.risk_level = risk

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

    if pregnancy.phone:
        msg = t("danger_sign_patient", pregnancy.language, ref=pregnancy.ref_number)
        send_patient_message(db, pregnancy, msg)
    log_action(db, user, "danger_sign", "pregnancy", pregnancy.id, body.sign_type)
    db.commit()
    db.refresh(pregnancy)
    return pregnancy


@router.get("/pregnancies/{pregnancy_id}/visits", response_model=list[VisitOut])
def list_visits(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)
    return (
        db.query(Visit)
        .filter(Visit.pregnancy_id == pregnancy_id)
        .order_by(Visit.visited_at.desc())
        .all()
    )


@router.put("/pregnancies/{pregnancy_id}/birth-prep", response_model=BirthPrepOut)
def update_birth_prep(
    pregnancy_id: int,
    body: BirthPrepUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_clinic_nurse(user, pregnancy)

    bp = pregnancy.birth_prep or BirthPrep(pregnancy_id=pregnancy_id)
    data = body.model_dump(exclude_unset=True)
    if "escort_phone" in data:
        data["escort_phone"] = normalize_phone(data["escort_phone"])
    for field, value in data.items():
        setattr(bp, field, value)
    db.add(bp)
    log_action(db, user, "update", "birth_prep", pregnancy_id)
    db.commit()
    db.refresh(bp)
    return _birth_prep_out(bp)


@router.get("/channels/status")
def channels_status(user: User = Depends(get_current_user)):
    return build_channel_status()


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Notification)
    if user.role == "admin":
        pass
    elif user.role == "nurse" and user.facility_id:
        preg_ids = db.query(Pregnancy.id).filter(Pregnancy.clinic_id == user.facility_id).subquery()
        query = query.filter(
            or_(
                Notification.pregnancy_id.in_(preg_ids),
                Notification.recipient == user.phone,
                Notification.recipient == user.email,
            )
        )
    elif user.role == "hospital" and user.facility_id:
        ref_ids = db.query(Referral.id).filter(Referral.to_facility_id == user.facility_id).subquery()
        preg_ids = (
            db.query(Referral.pregnancy_id).filter(Referral.to_facility_id == user.facility_id).subquery()
        )
        query = query.filter(
            or_(
                Notification.referral_id.in_(ref_ids),
                Notification.pregnancy_id.in_(preg_ids),
                Notification.recipient == user.phone,
                Notification.recipient == user.email,
            )
        )
    else:
        query = query.filter(False)
    return query.order_by(Notification.sent_at.desc()).limit(limit).all()


@router.post("/notifications/{notification_id}/retry", response_model=NotificationOut)
def retry_failed_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin", "nurse")
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed notifications can be retried")
    return retry_notification(db, notification)


@router.post("/referrals", response_model=ReferralOut)
def create_referral(
    body: ReferralCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, body.pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    if user.role != "nurse" or not user.facility_id:
        raise HTTPException(status_code=403, detail="Only clinic nurses can issue referrals")
    if pregnancy.clinic_id != user.facility_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if pregnancy.status != "active":
        raise HTTPException(status_code=400, detail="Cannot refer inactive patient")

    to_facility = db.get(Facility, body.to_facility_id)
    if not to_facility or to_facility.type != "hospital":
        raise HTTPException(status_code=400, detail="Invalid destination hospital")

    referral = Referral(
        ref_number=_next_ref_number(db, "REF"),
        pregnancy_id=pregnancy.id,
        from_facility_id=user.facility_id,
        to_facility_id=body.to_facility_id,
        issued_by=user.id,
        urgency=body.urgency,
        reason=body.reason,
        status=ReferralStatus.ISSUED.value,
    )
    db.add(referral)
    db.flush()

    patient_name = f"{pregnancy.first_name} {pregnancy.last_name}"
    brief = generate_referral_brief(pregnancy, body.reason)
    if brief:
        db.add(
            AiInsight(
                pregnancy_id=pregnancy.id,
                insight_type="referral_brief",
                language=brief["language"],
                content=brief["content"],
                ai_powered=brief["ai_powered"],
            )
        )
    hospital_alert = brief["content"] if brief else (
        f"SAFEPASS INCOMING: {patient_name}, {pregnancy.weeks_pregnant}wks. "
        f"{body.urgency.upper()}. Reason: {body.reason}. Ref: {referral.ref_number}"
    )
    hospital_users = db.query(User).filter(User.facility_id == body.to_facility_id, User.role == "hospital").all()
    for hu in hospital_users:
        notify_user(db, hu, hospital_alert, pregnancy_id=pregnancy.id, referral_id=referral.id)
    if body.urgency.lower() == "emergency" or pregnancy.risk_level in HIGH_RISK:
        alert_staff_by_voice(
            db,
            hospital_users,
            emergency_script(pregnancy, reason=body.reason),
            pregnancy.id,
            referral.id,
        )
    if pregnancy.phone:
        msg = t(
            "referral_patient",
            pregnancy.language,
            hospital=to_facility.name,
            ref=referral.ref_number,
            reason=body.reason,
        )
        send_patient_message(db, pregnancy, msg, referral_id=referral.id)

    log_action(db, user, "create", "referral", referral.id, referral.ref_number)
    db.commit()
    db.refresh(referral)
    return _referral_out(referral, db)


@router.get("/referrals", response_model=list[ReferralOut])
def list_referrals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Referral)
    if user.role == "nurse" and user.facility_id:
        query = query.filter(Referral.from_facility_id == user.facility_id)
    elif user.role == "hospital" and user.facility_id:
        query = query.filter(Referral.to_facility_id == user.facility_id)
    elif user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    referrals = query.order_by(Referral.issued_at.desc()).all()
    return [_referral_out(r, db) for r in referrals]


@router.patch("/referrals/{referral_id}/status", response_model=ReferralOut)
def update_referral_status(
    referral_id: int,
    status: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    referral = db.get(Referral, referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    assert_hospital_referral(user, referral)
    assert_valid_transition(referral.status, status)

    now = datetime.utcnow()
    referral.status = status
    if status == ReferralStatus.ACKNOWLEDGED.value:
        referral.acknowledged_at = now
    elif status == ReferralStatus.IN_TRANSIT.value:
        referral.departed_at = now
    elif status == ReferralStatus.ARRIVED.value:
        referral.arrived_at = now
    elif status == ReferralStatus.COMPLETED.value:
        referral.completed_at = now

    pregnancy = db.get(Pregnancy, referral.pregnancy_id)
    if pregnancy and status in STATUS_SMS:
        if pregnancy.phone:
            send_sms(
                db,
                pregnancy.phone,
                f"SafePass {referral.ref_number}: {STATUS_SMS[status]}",
                pregnancy_id=pregnancy.id,
                referral_id=referral.id,
            )
        from_f = db.get(Facility, referral.from_facility_id)
        if from_f:
            nurses = db.query(User).filter(User.role == "nurse", User.facility_id == from_f.id).all()
            for nurse in nurses:
                notify_user(
                    db,
                    nurse,
                    f"Referral {referral.ref_number} status: {status.replace('_', ' ')}.",
                    pregnancy_id=pregnancy.id,
                    referral_id=referral.id,
                )

    log_action(db, user, "status_change", "referral", referral.id, status)
    db.commit()
    db.refresh(referral)
    return _referral_out(referral, db)


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    preg_query = db.query(Pregnancy).filter(Pregnancy.status == "active")
    ref_query = db.query(Referral)
    if user.role == "nurse" and user.facility_id:
        preg_query = preg_query.filter(Pregnancy.clinic_id == user.facility_id)
        ref_query = ref_query.filter(Referral.from_facility_id == user.facility_id)
    elif user.role == "hospital" and user.facility_id:
        ref_query = ref_query.filter(Referral.to_facility_id == user.facility_id)
    elif user.role == "admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")

    pregnancies = preg_query.all()
    high_risk = [p for p in pregnancies if p.risk_level in ("amber", "red", "emergency")]
    referrals = ref_query.all()
    pending = [r for r in referrals if r.status in ("issued", "acknowledged", "in_transit")]
    month_start = _month_start()
    referrals_this_month = [r for r in referrals if r.issued_at >= month_start]

    today = datetime.utcnow().date()
    completed_today = [
        r for r in referrals
        if r.status == "completed" and r.completed_at and r.completed_at.date() == today
    ]

    return AnalyticsSummary(
        active_pregnancies=len(pregnancies),
        high_risk=len(high_risk),
        pending_referrals=len(pending),
        referrals_this_month=len(referrals_this_month),
        completed_today=len(completed_today),
    )


@router.get("/analytics/district", response_model=list[DistrictAnalytics])
def district_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    month_start = _month_start()
    districts: dict[str, DistrictAnalytics] = {}
    for facility in db.query(Facility).all():
        district = facility.district or "Unknown"
        if district not in districts:
            districts[district] = DistrictAnalytics(
                district=district,
                active_pregnancies=0,
                high_risk=0,
                pending_referrals=0,
                referrals_this_month=0,
                facilities=[],
            )
        entry = districts[district]
        if facility.type == "clinic":
            pregs = db.query(Pregnancy).filter(Pregnancy.clinic_id == facility.id, Pregnancy.status == "active").all()
            entry.active_pregnancies += len(pregs)
            entry.high_risk += len([p for p in pregs if p.risk_level in ("amber", "red", "emergency")])
        refs = db.query(Referral).filter(
            or_(Referral.from_facility_id == facility.id, Referral.to_facility_id == facility.id)
        ).all()
        entry.pending_referrals += len([r for r in refs if r.status in ("issued", "acknowledged", "in_transit")])
        entry.referrals_this_month += len([r for r in refs if r.issued_at >= month_start])
        entry.facilities.append({"id": facility.id, "name": facility.name, "type": facility.type})
    return list(districts.values())


@router.get("/anc-calendar", response_model=list[AncCalendarEntryOut])
def anc_calendar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "nurse" or not user.facility_id:
        raise HTTPException(status_code=403, detail="Clinic nurses only")
    entries = get_clinic_anc_calendar(db, user.facility_id)
    return [AncCalendarEntryOut.model_validate(e) for e in entries]


@router.get("/analytics/compliance", response_model=ComplianceReportOut)
def compliance_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, "admin")
    return ComplianceReportOut.model_validate(build_compliance_report(db))


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, "admin")
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/languages")
def list_languages():
    return [{"code": code, "name": LANGUAGE_NAMES[code]} for code in SUPPORTED_LANGUAGES]


@router.get("/pregnancies/{pregnancy_id}/education", response_model=list[EducationItemOut])
def get_education_schedule(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)
    return education_schedule(pregnancy)


@router.post("/pregnancies/{pregnancy_id}/send-education")
def trigger_education(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_clinic_nurse(user, pregnancy)
    result = send_education_for_pregnancy(db, pregnancy)
    log_action(db, user, "send", "education", pregnancy_id, str(result))
    return result


@router.get("/pregnancies/{pregnancy_id}/ai-insights", response_model=list[AiInsightOut])
def list_ai_insights(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = db.get(Pregnancy, pregnancy_id)
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)
    return (
        db.query(AiInsight)
        .filter(AiInsight.pregnancy_id == pregnancy_id)
        .order_by(AiInsight.created_at.desc())
        .limit(20)
        .all()
    )


@router.post("/pregnancies/{pregnancy_id}/ai-triage", response_model=AiInsightOut)
def refresh_ai_triage(
    pregnancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pregnancy = (
        db.query(Pregnancy)
        .options(joinedload(Pregnancy.danger_signs))
        .filter(Pregnancy.id == pregnancy_id)
        .first()
    )
    if not pregnancy:
        raise HTTPException(status_code=404, detail="Pregnancy not found")
    assert_pregnancy_access(db, user, pregnancy)
    last_sign = pregnancy.danger_signs[-1].sign_type if pregnancy.danger_signs else None
    triage = generate_triage_brief(pregnancy, last_sign)
    insight = AiInsight(
        pregnancy_id=pregnancy.id,
        insight_type="triage",
        language=triage["language"],
        content=triage["content"],
        ai_powered=triage["ai_powered"],
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


@router.get("/ai/dashboard-summary", response_model=AiDashboardSummaryOut)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = generate_dashboard_summary(db, user)
    log_action(db, user, "ai_summary", "dashboard", user.id)
    db.commit()
    return result


@router.get("/ai/chat/history", response_model=list[AiChatMessageOut])
def ai_chat_history(
    limit: int = 50,
    session_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _migrate_orphan_messages(db, user)
    query = db.query(AiChatMessage).filter(AiChatMessage.user_id == user.id)
    if session_id:
        query = query.filter(AiChatMessage.session_id == session_id)
    return query.order_by(AiChatMessage.created_at.asc()).limit(limit).all()


@router.get("/ai/chat/sessions", response_model=list[AiChatSessionOut])
def list_ai_chat_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _migrate_orphan_messages(db, user)
    db.commit()
    sessions = (
        db.query(AiChatSession)
        .filter(AiChatSession.user_id == user.id)
        .order_by(AiChatSession.updated_at.desc())
        .all()
    )
    results = []
    for session in sessions:
        messages = (
            db.query(AiChatMessage)
            .filter(AiChatMessage.session_id == session.id)
            .order_by(AiChatMessage.created_at.asc())
            .all()
        )
        preview = next((m.content for m in reversed(messages) if m.role == "user"), None)
        results.append(AiChatSessionOut(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages),
            preview=preview[:80] if preview else None,
        ))
    return results


@router.post("/ai/chat/sessions", response_model=AiChatSessionOut)
def create_ai_chat_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = AiChatSession(user_id=user.id, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return AiChatSessionOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
        preview=None,
    )


@router.delete("/ai/chat/sessions/{session_id}")
def delete_ai_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(AiChatSession).filter(
        AiChatSession.id == session_id,
        AiChatSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.query(AiChatMessage).filter(AiChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": True}


@router.delete("/ai/chat/history")
def clear_ai_chat_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.query(AiChatMessage).filter(AiChatMessage.user_id == user.id).delete()
    db.query(AiChatSession).filter(AiChatSession.user_id == user.id).delete()
    db.commit()
    return {"cleared": True}


@router.post("/ai/chat/transcribe", response_model=AiTranscribeResponse)
async def transcribe_ai_chat_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio recording")
    text = transcribe_audio(content, file.filename or "recording.webm")
    if not text:
        raise HTTPException(status_code=503, detail="Could not transcribe audio. Check OpenAI API key and billing.")
    return AiTranscribeResponse(text=text)


@router.post("/ai/chat/attach", response_model=AiAttachResponse)
async def attach_ai_chat_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    filename = file.filename or "upload.txt"
    try:
        message_type, excerpt = extract_file_content(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    suggested = f"[Attached: {filename}]\n\n{excerpt}\n\nPlease summarize this and tell me what actions I should take."
    return AiAttachResponse(
        filename=filename,
        excerpt=excerpt,
        message_type=message_type,
        suggested_message=suggested,
    )


@router.post("/ai/chat", response_model=AiChatResponse)
def send_ai_chat(
    body: AiChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _migrate_orphan_messages(db, user)
    session = _get_or_create_session(db, user, body.session_id)

    prior = (
        db.query(AiChatMessage)
        .filter(AiChatMessage.session_id == session.id)
        .order_by(AiChatMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(prior)]

    user_count = db.query(AiChatMessage).filter(
        AiChatMessage.session_id == session.id,
        AiChatMessage.role == "user",
    ).count()
    if session.title == "New chat" and user_count == 0:
        session.title = _session_title_from_message(body.message)

    message_type = "text"
    attachment_name = None
    if body.message.startswith("[Voice note]"):
        message_type = "audio"
    elif body.message.startswith("[Attached:"):
        message_type = "file"
        end = body.message.find("]")
        if end > 10:
            attachment_name = body.message[10:end]

    db.add(AiChatMessage(
        user_id=user.id,
        session_id=session.id,
        role="user",
        content=body.message,
        message_type=message_type,
        attachment_name=attachment_name,
        ai_powered=False,
    ))
    db.flush()

    result = ai_chat(db, user, body.message, history)
    assistant = AiChatMessage(
        user_id=user.id,
        session_id=session.id,
        role="assistant",
        content=result["content"],
        ai_powered=result["ai_powered"],
    )
    db.add(assistant)
    session.updated_at = datetime.utcnow()
    log_action(db, user, "ai_chat", "assistant", assistant.id, body.message[:120])
    db.commit()
    db.refresh(assistant)
    return AiChatResponse(
        reply=result["content"],
        ai_powered=result["ai_powered"],
        message_id=assistant.id,
        session_id=session.id,
    )
