"""Clinical care pathways — trimester staging, high-risk flags, MOHCC-aligned follow-ups."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Pregnancy, Referral, Visit

# WHO / MOHCC Zimbabwe focused ANC contact weeks
MOHCC_ANC_WEEKS = (12, 20, 26, 30, 34, 36, 38, 40)

FIRST_TRIMESTER_MAX = 13
SECOND_TRIMESTER_MAX = 27
LATE_PREGNANCY_MIN = 37
POST_TERM_MIN = 40

ADOLESCENT_MAX_AGE = 17
ADVANCED_MATERNAL_AGE = 35

TRIMESTER_LABELS = {
    "first": "1st trimester (early pregnancy)",
    "second": "2nd trimester",
    "third": "3rd trimester",
}

STAGE_LABELS = {
    "early": "Early pregnancy",
    "mid": "Mid pregnancy",
    "late": "Late pregnancy (≥37 weeks)",
    "post_term": "Post-term (≥40 weeks)",
}


def is_primigravida(pregnancy: Pregnancy) -> bool:
    """First pregnancy — no previous live births (parity 0)."""
    return (pregnancy.parity or 0) == 0


def get_trimester(weeks: int | None) -> str | None:
    if weeks is None:
        return None
    if weeks <= FIRST_TRIMESTER_MAX:
        return "first"
    if weeks <= SECOND_TRIMESTER_MAX:
        return "second"
    return "third"


def get_gestation_stage(weeks: int | None) -> str | None:
    if weeks is None:
        return None
    if weeks >= POST_TERM_MIN:
        return "post_term"
    if weeks >= LATE_PREGNANCY_MIN:
        return "late"
    if weeks <= FIRST_TRIMESTER_MAX:
        return "early"
    return "mid"


def is_multiple_gestation(pregnancy: Pregnancy) -> bool:
    return bool(pregnancy.multiple_gestation) or (pregnancy.fetal_count or 1) >= 2


def get_care_flags(pregnancy: Pregnancy) -> list[str]:
    flags: list[str] = []
    weeks = pregnancy.weeks_pregnant or 0

    if pregnancy.age is not None and pregnancy.age <= ADOLESCENT_MAX_AGE:
        flags.append("adolescent")
    if pregnancy.age is not None and pregnancy.age >= ADVANCED_MATERNAL_AGE:
        flags.append("advanced_age")
    if is_primigravida(pregnancy):
        flags.append("first_pregnancy")
    if is_multiple_gestation(pregnancy):
        flags.append("twins")
    if weeks <= FIRST_TRIMESTER_MAX:
        flags.append("early_pregnancy")
    if weeks >= LATE_PREGNANCY_MIN:
        flags.append("late_pregnancy")
    if weeks >= POST_TERM_MIN:
        flags.append("post_term")
    if (
        pregnancy.age is not None
        and pregnancy.age <= ADOLESCENT_MAX_AGE
        and not pregnancy.guardian_consent_recorded
    ):
        flags.append("guardian_consent_pending")
    return flags


def days_since_last_visit(db: Session, pregnancy_id: int) -> int | None:
    last = (
        db.query(Visit)
        .filter(Visit.pregnancy_id == pregnancy_id)
        .order_by(Visit.visited_at.desc())
        .first()
    )
    if not last:
        return None
    delta = datetime.utcnow() - last.visited_at
    return max(0, delta.days)


def _has_recent_visit(db: Session, pregnancy_id: int, days: int = 21) -> bool:
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Visit)
        .filter(Visit.pregnancy_id == pregnancy_id, Visit.visited_at >= since)
        .first()
        is not None
    )


def _anc_milestone_status(db: Session, pregnancy: Pregnancy, milestone: int, weeks: int) -> str:
    if weeks < milestone - 2:
        return "upcoming"
    if _has_recent_visit(db, pregnancy.id):
        return "completed"
    if weeks <= milestone + 2:
        return "due"
    return "overdue"


def _estimated_anc_date(pregnancy: Pregnancy, milestone_week: int) -> date | None:
    if pregnancy.lmp_date:
        return pregnancy.lmp_date + timedelta(weeks=milestone_week)
    if pregnancy.edd:
        return pregnancy.edd - timedelta(weeks=40 - milestone_week)
    return None


def get_anc_schedule(db: Session, pregnancy: Pregnancy) -> list[dict]:
    weeks = pregnancy.weeks_pregnant or 0
    schedule = []
    for milestone in MOHCC_ANC_WEEKS:
        schedule.append({
            "week": milestone,
            "status": _anc_milestone_status(db, pregnancy, milestone, weeks),
            "estimated_due_date": _estimated_anc_date(pregnancy, milestone),
        })
    return schedule


def get_clinic_anc_calendar(db: Session, clinic_id: int) -> list[dict]:
    """Patients at a clinic with ANC contacts due or overdue."""
    pregnancies = (
        db.query(Pregnancy)
        .filter(Pregnancy.clinic_id == clinic_id, Pregnancy.status == "active")
        .order_by(Pregnancy.weeks_pregnant.desc())
        .all()
    )
    entries = []
    for pregnancy in pregnancies:
        schedule = get_anc_schedule(db, pregnancy)
        current = next((s for s in schedule if s["status"] in ("due", "overdue")), None)
        if not current:
            continue
        entries.append({
            "pregnancy_id": pregnancy.id,
            "patient_name": f"{pregnancy.first_name} {pregnancy.last_name}",
            "ref_number": pregnancy.ref_number,
            "weeks_pregnant": pregnancy.weeks_pregnant,
            "anc_week": current["week"],
            "status": current["status"],
            "estimated_due_date": current["estimated_due_date"],
            "care_flags": get_care_flags(pregnancy),
            "risk_level": pregnancy.risk_level,
        })
    status_order = {"overdue": 0, "due": 1}

    def _flag_priority(flags: list[str]) -> int:
        if "post_term" in flags or "adolescent" in flags:
            return 0
        if "first_pregnancy" in flags or "twins" in flags:
            return 1
        return 2

    entries.sort(key=lambda e: (status_order.get(e["status"], 2), _flag_priority(e["care_flags"]), e["anc_week"]))
    return entries


def _has_hospital_referral(db: Session, pregnancy_id: int) -> bool:
    return (
        db.query(Referral)
        .filter(
            Referral.pregnancy_id == pregnancy_id,
            Referral.status.notin_(("cancelled", "no_show")),
        )
        .first()
        is not None
    )


def get_follow_up_tasks(db: Session, pregnancy: Pregnancy) -> list[dict]:
    """Return pending follow-up actions for nurses (MOHCC / constitutional care alignment)."""
    tasks: list[dict] = []
    weeks = pregnancy.weeks_pregnant or 0
    flags = get_care_flags(pregnancy)
    days_since = days_since_last_visit(db, pregnancy.id)

    if "guardian_consent_pending" in flags:
        tasks.append({
            "code": "guardian_consent",
            "priority": "high",
            "title": "Record guardian/parent consent",
            "detail": (
                "Patient is under 18. Zimbabwe health practice requires guardian awareness "
                "and documented consent for adolescent ANC (Constitution s.76 — right to health; "
                "Child Protection Framework)."
            ),
        })

    if "first_pregnancy" in flags:
        tasks.append({
            "code": "primigravida_counselling",
            "priority": "medium" if weeks < 28 else "high",
            "title": "First pregnancy — ANC counselling & birth education",
            "detail": (
                f"Primigravida (G{pregnancy.gravida or 1}P{pregnancy.parity or 0}): first labour carries higher "
                "risk without preparation. Complete danger-sign education, birth plan, and escort planning."
            ),
        })
        if weeks >= 32 and pregnancy.birth_prep and (pregnancy.birth_prep.completed_pct or 0) < 60:
            tasks.append({
                "code": "primigravida_birth_prep",
                "priority": "high",
                "title": "First pregnancy — complete birth plan before labour",
                "detail": (
                    "Primigravida at ≥32 weeks with incomplete birth prep. Confirm facility, "
                    "transport, escort, and emergency savings before labour onset."
                ),
            })

    if "adolescent" in flags and "early_pregnancy" in flags:
        overdue = days_since is None or days_since >= 14
        if overdue:
            tasks.append({
                "code": "adolescent_early_anc",
                "priority": "high",
                "title": "Adolescent early-pregnancy ANC follow-up",
                "detail": (
                    "Fortnightly ANC contact recommended for under-18 mothers in the 1st trimester. "
                    f"Last visit: {days_since if days_since is not None else 'none recorded'} days ago."
                ),
            })

    if "twins" in flags:
        tasks.append({
            "code": "twins_monitoring",
            "priority": "high" if weeks >= 28 else "medium",
            "title": "Multiple pregnancy care plan",
            "detail": (
                "Twin/multiple gestation — elevated monitoring, earlier birth-planning, "
                "and hospital-level delivery planning per MOHCC high-risk pregnancy guidance."
            ),
        })
        if weeks >= 28 and not _has_hospital_referral(db, pregnancy.id):
            tasks.append({
                "code": "twins_referral",
                "priority": "high",
                "title": "Consider hospital referral for twins",
                "detail": "At ≥28 weeks, multiple gestation should have hospital delivery plan and referral on file.",
            })

    if "late_pregnancy" in flags and pregnancy.birth_prep:
        pct = pregnancy.birth_prep.completed_pct or 0
        if pct < 80:
            tasks.append({
                "code": "late_birth_prep",
                "priority": "high",
                "title": "Complete birth preparedness urgently",
                "detail": f"Late pregnancy with birth prep only {pct}% complete. Escort, transport, and facility must be confirmed.",
            })

    if "post_term" in flags:
        tasks.append({
            "code": "post_term_escalation",
            "priority": "emergency",
            "title": "Post-term monitoring escalation",
            "detail": "≥40 weeks — daily monitoring, assess for induction/referral per MOHCC protocol.",
        })

    schedule = get_anc_schedule(db, pregnancy)
    for item in schedule:
        if item["status"] == "overdue":
            tasks.append({
                "code": f"anc_milestone_{item['week']}",
                "priority": "medium",
                "title": f"ANC contact overdue (week {item['week']})",
                "detail": f"MOHCC focused ANC schedule — week {item['week']} contact is overdue.",
            })
            break
        if item["status"] == "due":
            tasks.append({
                "code": f"anc_milestone_{item['week']}",
                "priority": "medium",
                "title": f"ANC contact due (week {item['week']})",
                "detail": f"MOHCC focused ANC schedule — week {item['week']} contact is due now.",
            })
            break

    return tasks


def build_compliance_report(db: Session) -> dict:
    """District compliance — adolescent cases without guardian consent."""
    adolescents = (
        db.query(Pregnancy)
        .filter(Pregnancy.status == "active", Pregnancy.age.isnot(None), Pregnancy.age <= ADOLESCENT_MAX_AGE)
        .all()
    )
    all_active = db.query(Pregnancy).filter(Pregnancy.status == "active").all()
    pending = [p for p in adolescents if not p.guardian_consent_recorded]
    primigravida = [p for p in all_active if is_primigravida(p)]

    by_district: dict[str, dict] = {}
    for pregnancy in pending:
        facility = pregnancy.clinic
        district = (facility.district if facility else None) or "Unknown"
        if district not in by_district:
            by_district[district] = {"district": district, "pending_count": 0, "cases": []}
        by_district[district]["pending_count"] += 1
        by_district[district]["cases"].append({
            "pregnancy_id": pregnancy.id,
            "ref_number": pregnancy.ref_number,
            "patient_name": f"{pregnancy.first_name} {pregnancy.last_name}",
            "age": pregnancy.age,
            "weeks_pregnant": pregnancy.weeks_pregnant,
            "facility_name": facility.name if facility else "Unassigned",
            "gravida": pregnancy.gravida or 1,
            "parity": pregnancy.parity or 0,
            "first_pregnancy": is_primigravida(pregnancy),
        })

    return {
        "total_adolescent_active": len(adolescents),
        "guardian_consent_pending": len(pending),
        "primigravida_active": len(primigravida),
        "districts": sorted(by_district.values(), key=lambda d: d["pending_count"], reverse=True),
    }


def build_care_pathway(db: Session, pregnancy: Pregnancy) -> dict:
    weeks = pregnancy.weeks_pregnant
    trimester = get_trimester(weeks)
    stage = get_gestation_stage(weeks)
    flags = get_care_flags(pregnancy)
    tasks = get_follow_up_tasks(db, pregnancy)
    anc_schedule = get_anc_schedule(db, pregnancy)

    protocol_notes = [
        "Aligned with Zimbabwe MOHCC focused antenatal care (8 contacts) and WHO danger-sign principles.",
        "Patient consent recorded at registration; adolescents require guardian consent documentation.",
        "Risk tier is rule-based — clinical decisions remain with authorised nurse/midwife.",
    ]
    if "twins" in flags:
        protocol_notes.append("Multiple gestation: classify as high-risk; plan facility delivery with obstetric capacity.")
    if "adolescent" in flags:
        protocol_notes.append("Adolescent pregnancy: enhanced psychosocial support and confidential, non-judgemental care.")
    if "first_pregnancy" in flags:
        protocol_notes.append(
            "Primigravida (first pregnancy): intensify birth-preparedness education and ANC attendance; "
            "first labour has higher complication risk without early counselling."
        )

    return {
        "trimester": trimester,
        "trimester_label": TRIMESTER_LABELS.get(trimester or "", trimester or ""),
        "gestation_stage": stage,
        "gestation_stage_label": STAGE_LABELS.get(stage or "", stage or ""),
        "care_flags": flags,
        "follow_up_tasks": tasks,
        "protocol_notes": protocol_notes,
        "days_since_last_visit": days_since_last_visit(db, pregnancy.id),
        "mohcc_anc_weeks": list(MOHCC_ANC_WEEKS),
        "gravida": pregnancy.gravida or 1,
        "parity": pregnancy.parity or 0,
        "anc_schedule": anc_schedule,
    }
