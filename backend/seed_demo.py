"""Load rich demo data for testing all SafePass features.

Usage:
  python seed_demo.py          # load if missing
  python seed_demo.py --fresh  # replace patients/referrals with full demo set
"""
import sys
from datetime import date, datetime, timedelta

from app.auth import hash_password
from app.database import SessionLocal
from app.models import (
    AiChatMessage,
    AiChatSession,
    AiInsight,
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
from app.services.risk_engine import calculate_risk
from seed import seed


def _clear_demo_clinical_data(db):
    db.query(Notification).delete()
    db.query(AiInsight).delete()
    db.query(Visit).delete()
    db.query(DangerSign).delete()
    db.query(Referral).delete()
    db.query(BirthPrep).delete()
    db.query(Pregnancy).delete()
    db.flush()


def seed_demo(fresh: bool = False):
    seed()
    db = SessionLocal()
    try:
        exists = db.query(Pregnancy).filter(Pregnancy.ref_number == "SP-2026-0001").first()
        if exists and not fresh:
            chw = db.query(CHW).first()
            if chw:
                chw.phone = "+263773566281"
            _reset_demo_passwords(db)
            db.commit()
            print("Demo data already loaded. CHW phone refreshed.")
            _print_logins()
            return

        if fresh and db.query(Pregnancy).count():
            print("Replacing existing patient data with full demo set...")
            _clear_demo_clinical_data(db)

        mashava = db.query(Facility).filter(Facility.name == "Mashava Clinic").first()
        gutu = db.query(Facility).filter(Facility.name == "Gutu District Hospital").first()
        chw = db.query(CHW).first()
        nurse = db.query(User).filter(User.email == "chipo@mashava.clinic").first()
        hospital_user = db.query(User).filter(User.email == "farai@gutu.hospital").first()

        if not all([mashava, gutu, chw, nurse, hospital_user]):
            print("Run base seed first — missing facilities or users.")
            return

        chw.phone = "+263773566281"
        today = date.today()

        patients = [
            {
                "ref": "SP-2026-0001",
                "first_name": "Grace",
                "last_name": "Moyo",
                "age": 19,
                "weeks": 34,
                "village": "Mashava",
                "phone": "+263773566281",
                "risk_flags": {"hypertension": True, "parity": 0, "gravida": 1},
                "language": "sn",
                "birth_prep": dict(
                    facility_identified=True,
                    escort_identified=False,
                    danger_education_done=True,
                    bag_prepared=False,
                ),
                "danger_signs": [("bleeding", "Vaginal bleeding reported via USSD")],
            },
            {
                "ref": "SP-2026-0002",
                "first_name": "Tendai",
                "last_name": "Ndlovu",
                "age": 32,
                "weeks": 28,
                "village": "Chatsworth",
                "phone": "+263772001002",
                "risk_flags": {"previous_cs": True, "hypertension": True, "parity": 1, "gravida": 2},
                "language": "en",
                "birth_prep": dict(
                    facility_identified=True,
                    escort_identified=True,
                    escort_phone="+263772009999",
                    transport_plan="Community ambulance + relative with fuel money",
                    emergency_savings=25.0,
                    danger_education_done=True,
                    bag_prepared=True,
                ),
                "danger_signs": [("severe_headache", "Persistent headache 2 days")],
            },
            {
                "ref": "SP-2026-0003",
                "first_name": "Chipo",
                "last_name": "Sithole",
                "age": 26,
                "weeks": 32,
                "village": "Mashava",
                "phone": "+263772001003",
                "risk_flags": {"parity": 1, "gravida": 2},
                "language": "en",
                "birth_prep": dict(
                    facility_identified=True,
                    escort_identified=True,
                    danger_education_done=False,
                    bag_prepared=False,
                ),
                "danger_signs": [("swelling", "Facial and leg swelling")],
            },
            {
                "ref": "SP-2026-0004",
                "first_name": "Rutendo",
                "last_name": "Chikwanha",
                "age": 24,
                "weeks": 20,
                "village": "Nyika",
                "phone": "+263772001004",
                "risk_flags": {"parity": 0, "gravida": 1},
                "language": "nd",
                "birth_prep": dict(
                    facility_identified=True,
                    escort_identified=True,
                    escort_phone="+263772001010",
                    transport_plan="Paid taxi to Mashava Clinic",
                    emergency_savings=40.0,
                    danger_education_done=True,
                    bag_prepared=True,
                ),
                "danger_signs": [],
            },
            {
                "ref": "SP-2026-0005",
                "first_name": "Nyasha",
                "last_name": "Dube",
                "age": 17,
                "weeks": 16,
                "village": "Mashava",
                "phone": "+263772001005",
                "risk_flags": {"parity": 0, "gravida": 1, "guardian_consent_recorded": True},
                "language": "sn",
                "birth_prep": dict(facility_identified=False),
                "danger_signs": [],
            },
        ]

        created = []
        for spec in patients:
            flags = spec["risk_flags"]
            edd = today + timedelta(weeks=max(40 - spec["weeks"], 0))
            lmp = today - timedelta(weeks=spec["weeks"])
            pregnancy = Pregnancy(
                ref_number=spec["ref"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                age=spec["age"],
                weeks_pregnant=spec["weeks"],
                lmp_date=lmp,
                edd=edd,
                village=spec["village"],
                phone=spec["phone"],
                chw_id=chw.id,
                clinic_id=mashava.id,
                previous_cs=flags.get("previous_cs", False),
                hypertension=flags.get("hypertension", False),
                multiple_gestation=flags.get("multiple_gestation", False),
                fetal_count=flags.get("fetal_count", 1),
                guardian_consent_recorded=flags.get("guardian_consent_recorded", spec["age"] >= 18),
                gravida=flags.get("gravida", 1),
                parity=flags.get("parity", 0),
                consent_recorded=True,
                language=spec["language"],
                whatsapp_opt_in=True,
                status="active",
            )
            sign_types = [s[0] for s in spec["danger_signs"]]
            _, pregnancy.risk_level = calculate_risk(pregnancy, sign_types)
            db.add(pregnancy)
            db.flush()

            bp = BirthPrep(pregnancy_id=pregnancy.id, **spec["birth_prep"])
            db.add(bp)

            for sign_type, description in spec["danger_signs"]:
                db.add(DangerSign(
                    pregnancy_id=pregnancy.id,
                    sign_type=sign_type,
                    description=description,
                    reporter_type="chw",
                    reporter_id=chw.id,
                    ai_brief=(
                        f"Triage: {spec['first_name']} — {sign_type.replace('_', ' ')} at {spec['weeks']} weeks. "
                        f"Risk {pregnancy.risk_level.upper()}. Urgent clinic review advised."
                    ),
                    reported_at=datetime.utcnow() - timedelta(days=1),
                ))

            db.add(Visit(
                pregnancy_id=pregnancy.id,
                facility_id=mashava.id,
                chw_id=chw.id,
                visit_type="check_in",
                notes=f"Routine ANC check-in — {spec['weeks']} weeks.",
                visited_at=datetime.utcnow() - timedelta(days=3),
            ))
            created.append(pregnancy)

        grace, tendai, chipo = created[0], created[1], created[2]

        db.add(AiInsight(
            pregnancy_id=grace.id,
            insight_type="triage",
            language="sn",
            content="Emergency: bleeding at 34 weeks with elevated BP history. Immediate referral recommended.",
            ai_powered=False,
        ))

        ref1 = Referral(
            ref_number="REF-2026-0001",
            pregnancy_id=grace.id,
            from_facility_id=mashava.id,
            to_facility_id=gutu.id,
            issued_by=nurse.id,
            urgency="emergency",
            reason="Vaginal bleeding at 34 weeks — pre-eclampsia suspected",
            status=ReferralStatus.IN_TRANSIT.value,
            issued_at=datetime.utcnow() - timedelta(hours=2),
            acknowledged_at=datetime.utcnow() - timedelta(hours=1, minutes=30),
            departed_at=datetime.utcnow() - timedelta(minutes=45),
        )
        ref2 = Referral(
            ref_number="REF-2026-0002",
            pregnancy_id=tendai.id,
            from_facility_id=mashava.id,
            to_facility_id=gutu.id,
            issued_by=nurse.id,
            urgency="red",
            reason="Previous C-section + severe headache — hospital delivery plan",
            status=ReferralStatus.ACKNOWLEDGED.value,
            issued_at=datetime.utcnow() - timedelta(days=1),
            acknowledged_at=datetime.utcnow() - timedelta(hours=20),
        )
        ref3 = Referral(
            ref_number="REF-2026-0003",
            pregnancy_id=chipo.id,
            from_facility_id=mashava.id,
            to_facility_id=gutu.id,
            issued_by=nurse.id,
            urgency="amber",
            reason="Swelling and moderate risk — assessment requested",
            status=ReferralStatus.ISSUED.value,
            issued_at=datetime.utcnow() - timedelta(hours=4),
        )
        db.add_all([ref1, ref2, ref3])
        db.flush()

        sample_notifications = [
            (grace.phone, "SafePass SP-2026-0001: Danger sign recorded. Go to clinic if symptoms worsen.", "sms"),
            (grace.phone, "SafePass SP-2026-0001: Referral REF-2026-0001 issued to Gutu District Hospital.", "sms"),
            (hospital_user.phone, "SAFEPASS INCOMING: Grace Moyo, 34wks. EMERGENCY. Ref: REF-2026-0001", "sms"),
            (tendai.phone, "SafePass: Your ANC education tip for week 28 — rest and monitor swelling.", "whatsapp"),
            (nurse.phone, "SafePass clinic alert: 1 emergency patient needs follow-up today.", "sms"),
        ]
        for recipient, message, channel in sample_notifications:
            db.add(Notification(
                pregnancy_id=grace.id,
                channel=channel,
                recipient=recipient,
                message=message,
                status="sent",
                provider_ref="demo-seed",
            ))

        _reset_demo_passwords(db)
        db.commit()
        print("Demo data loaded successfully.")
        _print_logins()
        print("\nDemo highlights:")
        print("  • 5 patients (emergency / red / amber / green / adolescent)")
        print("  • 3 referrals (in transit / acknowledged / issued)")
        print("  • Danger signs, visits, birth prep, SMS log entries")
        print("  • CHW phone: +263773566281 (for USSD testing)")
    finally:
        db.close()


def _reset_demo_passwords(db):
    for email in ["chipo@mashava.clinic", "farai@gutu.hospital", "admin@safepass.co.zw"]:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.password_hash = hash_password("changeme")
            user.is_active = True


def _print_logins():
    print("\nLogins (password: changeme):")
    print("  Nurse:    chipo@mashava.clinic")
    print("  Hospital: farai@gutu.hospital")
    print("  Admin:    admin@safepass.co.zw")


if __name__ == "__main__":
    seed_demo(fresh="--fresh" in sys.argv)
