import os
import tempfile

import pytest
from fastapi.testclient import TestClient

TEST_DB = os.path.join(tempfile.gettempdir(), "safepass_pytest.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SMS_PROVIDER"] = "log"
os.environ["WHATSAPP_PROVIDER"] = "log"
os.environ["VOICE_PROVIDER"] = "log"
os.environ["AIRTIME_PROVIDER"] = "log"

from app.database import Base, SessionLocal, engine, get_db
from app.auth import hash_password
from app.models import CHW, Facility, Pregnancy, User
from main import app


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    clinic = Facility(name="Test Clinic", type="clinic", district="Gutu")
    hospital = Facility(name="Test Hospital", type="hospital", district="Gutu")
    session.add_all([clinic, hospital])
    session.flush()
    nurse = User(
        email="nurse@test.com",
        password_hash=hash_password("password123"),
        name="Nurse",
        role="nurse",
        facility_id=clinic.id,
        phone="+263771111111",
    )
    hospital_user = User(
        email="hospital@test.com",
        password_hash=hash_password("password123"),
        name="Hospital",
        role="hospital",
        facility_id=hospital.id,
        phone="+263772222222",
    )
    chw = CHW(name="CHW", phone="+263773333333", facility_id=clinic.id)
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("password123"),
        name="Admin",
        role="admin",
        phone="+263773333334",
    )
    session.add_all([nurse, hospital_user, chw, admin])
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client, email):
    res = client.post("/api/auth/login/json", json={"email": email, "password": "password123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_auth_and_pregnancy_flow(client, db):
    token = _login(client, "nurse@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/pregnancies",
        headers=headers,
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "age": 28,
            "weeks_pregnant": 20,
            "village": "Mashava",
            "phone": "+263774444444",
            "consent_recorded": True,
        },
    )
    assert create.status_code == 200
    pregnancy_id = create.json()["id"]
    assert create.json()["edd"] is not None

    hospital_token = _login(client, "hospital@test.com")
    denied = client.get(f"/api/pregnancies/{pregnancy_id}", headers={"Authorization": f"Bearer {hospital_token}"})
    assert denied.status_code == 403


def test_referral_state_machine(client, db):
    nurse_token = _login(client, "nurse@test.com")
    hospital_token = _login(client, "hospital@test.com")
    nurse_headers = {"Authorization": f"Bearer {nurse_token}"}
    hospital_headers = {"Authorization": f"Bearer {hospital_token}"}

    clinic = db.query(Facility).filter(Facility.type == "clinic").first()
    hospital = db.query(Facility).filter(Facility.type == "hospital").first()
    pregnancy = Pregnancy(
        ref_number="SP-2026-0001",
        first_name="Test",
        last_name="Patient",
        age=25,
        weeks_pregnant=30,
        clinic_id=clinic.id,
        status="active",
    )
    db.add(pregnancy)
    db.commit()

    referral = client.post(
        "/api/referrals",
        headers=nurse_headers,
        json={"pregnancy_id": pregnancy.id, "to_facility_id": hospital.id, "urgency": "urgent", "reason": "BP high"},
    )
    assert referral.status_code == 200
    ref_id = referral.json()["id"]

    bad = client.patch(f"/api/referrals/{ref_id}/status?status=completed", headers=hospital_headers)
    assert bad.status_code == 400

    ok = client.patch(f"/api/referrals/{ref_id}/status?status=acknowledged", headers=hospital_headers)
    assert ok.status_code == 200


def test_ussd_validation(client):
    res = client.post("/ussd/callback", json={"phone": "+263773333333", "text": "1*Jane*Doe*bad*20*Village*1*2*0*2*0"})
    assert res.status_code == 200
    assert "Invalid age" in res.json()["response"]


def test_voice_callback_speaks_prompt(client, db):
    from app.models import VoicePrompt

    db.add(VoicePrompt(request_id="req-1", recipient="+263771100001", message="SafePass emergency. Patient Jane Doe."))
    db.commit()
    res = client.post(
        "/voice/callback",
        data={"isActive": "1", "clientRequestId": "req-1", "destinationNumber": "+263771100001"},
    )
    assert res.status_code == 200
    assert res.text.startswith("<?xml")
    assert "Jane Doe" in res.text
    assert "<Say" in res.text


def test_chw_register_sends_airtime_once(client, db):
    clinic = db.query(Facility).filter(Facility.type == "clinic").first()
    chw = db.query(CHW).first()
    chw.facility_id = clinic.id
    db.commit()

    first = client.post(
        "/ussd/callback",
        json={"phone": chw.phone, "text": "1*Jane*Doe*24*20*Mashava*2*2*1*2*0"},
    )
    assert first.status_code == 200
    assert "Registered" in first.json()["response"]
    assert "Airtime reward sent" in first.json()["response"]

    from app.models import AirtimeReward, Notification

    rewards = db.query(AirtimeReward).filter(AirtimeReward.chw_id == chw.id, AirtimeReward.reason == "register").all()
    assert len(rewards) == 1
    assert db.query(Notification).filter(Notification.channel == "airtime").count() >= 1


def test_channel_status_includes_voice_and_airtime(client):
    token = _login(client, "admin@test.com")
    res = client.get("/api/channels/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert "voice_provider" in body
    assert "airtime_provider" in body
    assert "voice_callback_url" in body


def test_ussd_africas_talking_plain_text(client, db):
    clinic = db.query(Facility).filter(Facility.type == "clinic").first()
    chw = CHW(name="Live CHW", phone="+263771234567", village="Mashava", facility_id=clinic.id)
    db.add(chw)
    db.commit()

    res = client.post(
        "/ussd/callback",
        data={"sessionId": "AT-123", "phoneNumber": "+263771234567", "text": ""},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert res.text.startswith("CON SafePass")


def test_twins_elevates_risk(client):
    token = _login(client, "nurse@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        "/api/pregnancies",
        headers=headers,
        json={
            "first_name": "Twin",
            "last_name": "Mother",
            "age": 30,
            "weeks_pregnant": 28,
            "village": "Mashava",
            "multiple_gestation": True,
            "fetal_count": 2,
            "consent_recorded": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["risk_level"] in ("amber", "red")


def test_adolescent_care_pathway(client, db):
    token = _login(client, "nurse@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    create = client.post(
        "/api/pregnancies",
        headers=headers,
        json={
            "first_name": "Young",
            "last_name": "Mother",
            "age": 16,
            "weeks_pregnant": 10,
            "village": "Mashava",
            "consent_recorded": True,
            "guardian_consent_recorded": False,
        },
    )
    assert create.status_code == 200
    pid = create.json()["id"]
    detail = client.get(f"/api/pregnancies/{pid}", headers=headers)
    pathway = detail.json()["care_pathway"]
    assert "adolescent" in pathway["care_flags"]
    assert "guardian_consent_pending" in pathway["care_flags"]
    assert any(t["code"] == "guardian_consent" for t in pathway["follow_up_tasks"])


def test_primigravida_risk_and_pathway(client):
    token = _login(client, "nurse@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        "/api/pregnancies",
        headers=headers,
        json={
            "first_name": "First",
            "last_name": "Time",
            "age": 22,
            "weeks_pregnant": 14,
            "village": "Mashava",
            "parity": 0,
            "gravida": 1,
            "consent_recorded": True,
        },
    )
    assert res.status_code == 200
    pid = res.json()["id"]
    detail = client.get(f"/api/pregnancies/{pid}", headers=headers)
    pathway = detail.json()["care_pathway"]
    assert "first_pregnancy" in pathway["care_flags"]
    assert pathway["parity"] == 0
    assert len(pathway["anc_schedule"]) == 8


def test_compliance_report_admin(client, db):
    clinic = db.query(Facility).filter(Facility.type == "clinic").first()
    db.add(
        Pregnancy(
            ref_number="SP-2026-0099",
            first_name="Teen",
            last_name="Mother",
            age=16,
            weeks_pregnant=12,
            clinic_id=clinic.id,
            status="active",
            parity=0,
            gravida=1,
            guardian_consent_recorded=False,
        )
    )
    db.commit()
    token = _login(client, "admin@test.com")
    res = client.get("/api/analytics/compliance", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["guardian_consent_pending"] >= 1
