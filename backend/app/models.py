import enum
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskLevel(str, enum.Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    EMERGENCY = "emergency"


class ReferralStatus(str, enum.Enum):
    ISSUED = "issued"
    ACKNOWLEDGED = "acknowledged"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    district: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))

    users: Mapped[list["User"]] = relationship(back_populates="facility")
    pregnancies: Mapped[list["Pregnancy"]] = relationship(back_populates="clinic")


class CHW(Base):
    __tablename__ = "chws"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    village: Mapped[str | None] = mapped_column(String(100))
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"))

    pregnancies: Mapped[list["Pregnancy"]] = relationship(back_populates="chw")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(20))
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reset_token: Mapped[str | None] = mapped_column(String(64))
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime)

    facility: Mapped[Facility | None] = relationship(back_populates="users")


class Pregnancy(Base):
    __tablename__ = "pregnancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref_number: Mapped[str] = mapped_column(String(20), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    lmp_date: Mapped[Date | None] = mapped_column(Date)
    edd: Mapped[Date | None] = mapped_column(Date)
    village: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    weeks_pregnant: Mapped[int | None] = mapped_column(Integer)
    chw_id: Mapped[int | None] = mapped_column(ForeignKey("chws.id"))
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"))
    risk_level: Mapped[str] = mapped_column(String(20), default=RiskLevel.GREEN.value)
    status: Mapped[str] = mapped_column(String(20), default="active")
    previous_cs: Mapped[bool] = mapped_column(Boolean, default=False)
    hypertension: Mapped[bool] = mapped_column(Boolean, default=False)
    multiple_gestation: Mapped[bool] = mapped_column(Boolean, default=False)
    fetal_count: Mapped[int] = mapped_column(Integer, default=1)
    guardian_consent_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    gravida: Mapped[int] = mapped_column(Integer, default=1)
    parity: Mapped[int] = mapped_column(Integer, default=0)
    consent_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(5), default="en")
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chw: Mapped[CHW | None] = relationship(back_populates="pregnancies")
    clinic: Mapped[Facility | None] = relationship(back_populates="pregnancies")
    danger_signs: Mapped[list["DangerSign"]] = relationship(back_populates="pregnancy")
    referrals: Mapped[list["Referral"]] = relationship(back_populates="pregnancy")
    birth_prep: Mapped["BirthPrep | None"] = relationship(back_populates="pregnancy", uselist=False)
    visits: Mapped[list["Visit"]] = relationship(back_populates="pregnancy")


class BirthPrep(Base):
    __tablename__ = "birth_prep"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"), unique=True)
    facility_identified: Mapped[bool] = mapped_column(Boolean, default=False)
    escort_identified: Mapped[bool] = mapped_column(Boolean, default=False)
    escort_phone: Mapped[str | None] = mapped_column(String(20))
    transport_plan: Mapped[str | None] = mapped_column(Text)
    emergency_savings: Mapped[float | None] = mapped_column(Float)
    danger_education_done: Mapped[bool] = mapped_column(Boolean, default=False)
    bag_prepared: Mapped[bool] = mapped_column(Boolean, default=False)

    pregnancy: Mapped[Pregnancy] = relationship(back_populates="birth_prep")

    @property
    def completed_pct(self) -> int:
        checks = [
            self.facility_identified,
            self.escort_identified,
            self.danger_education_done,
            self.bag_prepared,
        ]
        if self.transport_plan:
            checks.append(True)
        if self.emergency_savings:
            checks.append(True)
        if self.escort_phone:
            checks.append(True)
        return int(sum(checks) / len(checks) * 100) if checks else 0


class DangerSign(Base):
    __tablename__ = "danger_signs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"))
    sign_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    reporter_type: Mapped[str | None] = mapped_column(String(20))
    reporter_id: Mapped[int | None] = mapped_column(Integer)
    ai_brief: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pregnancy: Mapped[Pregnancy] = relationship(back_populates="danger_signs")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"))
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"))
    chw_id: Mapped[int | None] = mapped_column(ForeignKey("chws.id"))
    visit_type: Mapped[str] = mapped_column(String(30), default="check_in")
    notes: Mapped[str | None] = mapped_column(Text)
    visited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pregnancy: Mapped[Pregnancy] = relationship(back_populates="visits")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EducationLog(Base):
    __tablename__ = "education_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"))
    week_milestone: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AiInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"))
    insight_type: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(5), default="en")
    content: Mapped[str] = mapped_column(Text)
    ai_powered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AiChatSession(Base):
    __tablename__ = "ai_chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(120), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["AiChatMessage"]] = relationship(back_populates="session")


class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("ai_chat_sessions.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    attachment_name: Mapped[str | None] = mapped_column(String(255))
    ai_powered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["AiChatSession | None"] = relationship(back_populates="messages")


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref_number: Mapped[str] = mapped_column(String(20), unique=True)
    pregnancy_id: Mapped[int] = mapped_column(ForeignKey("pregnancies.id"))
    from_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    to_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    urgency: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ReferralStatus.ISSUED.value)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    departed_at: Mapped[datetime | None] = mapped_column(DateTime)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    pregnancy: Mapped[Pregnancy] = relationship(back_populates="referrals")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pregnancy_id: Mapped[int | None] = mapped_column(ForeignKey("pregnancies.id"))
    referral_id: Mapped[int | None] = mapped_column(ForeignKey("referrals.id"))
    channel: Mapped[str] = mapped_column(String(10))
    recipient: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="sent")
    provider_ref: Mapped[str | None] = mapped_column(String(100))
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UssdSession(Base):
    __tablename__ = "ussd_sessions"

    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VoicePrompt(Base):
    __tablename__ = "voice_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    session_id: Mapped[str | None] = mapped_column(String(100))
    recipient: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AirtimeReward(Base):
    __tablename__ = "airtime_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chw_id: Mapped[int] = mapped_column(ForeignKey("chws.id"))
    pregnancy_id: Mapped[int | None] = mapped_column(ForeignKey("pregnancies.id"))
    reason: Mapped[str] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    amount: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="sent")
    provider_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
