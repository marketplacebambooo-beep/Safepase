from datetime import date, datetime

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    phone: str | None = None
    facility_id: int | None
    facility_name: str | None = None

    class Config:
        from_attributes = True


class FacilityOut(BaseModel):
    id: int
    name: str
    type: str
    district: str | None

    class Config:
        from_attributes = True


class DangerSignOut(BaseModel):
    id: int
    sign_type: str
    description: str | None
    ai_brief: str | None = None
    reported_at: datetime

    class Config:
        from_attributes = True


class PregnancyOut(BaseModel):
    id: int
    ref_number: str
    first_name: str
    last_name: str
    age: int | None
    village: str | None
    phone: str | None
    weeks_pregnant: int | None
    lmp_date: date | None = None
    edd: date | None = None
    risk_level: str
    status: str
    clinic_id: int | None
    chw_id: int | None
    previous_cs: bool
    hypertension: bool
    multiple_gestation: bool = False
    fetal_count: int = 1
    guardian_consent_recorded: bool = False
    gravida: int = 1
    parity: int = 0
    consent_recorded: bool = False
    language: str = "en"
    whatsapp_opt_in: bool = True
    created_at: datetime
    danger_signs: list[DangerSignOut] = []

    class Config:
        from_attributes = True


class ReferralCreate(BaseModel):
    pregnancy_id: int
    to_facility_id: int
    urgency: str
    reason: str


class ReferralOut(BaseModel):
    id: int
    ref_number: str
    pregnancy_id: int
    from_facility_id: int
    to_facility_id: int
    urgency: str
    reason: str
    status: str
    issued_at: datetime
    acknowledged_at: datetime | None
    departed_at: datetime | None
    arrived_at: datetime | None
    completed_at: datetime | None
    patient_name: str | None = None
    patient_weeks: int | None = None
    from_facility_name: str | None = None
    to_facility_name: str | None = None

    class Config:
        from_attributes = True


class AnalyticsSummary(BaseModel):
    active_pregnancies: int
    high_risk: int
    pending_referrals: int
    referrals_this_month: int
    completed_today: int = 0


class NotificationOut(BaseModel):
    id: int
    channel: str
    recipient: str
    message: str
    status: str = "sent"
    provider_ref: str | None = None
    sent_at: datetime

    class Config:
        from_attributes = True


class BirthPrepOut(BaseModel):
    facility_identified: bool = False
    escort_identified: bool = False
    escort_phone: str | None = None
    transport_plan: str | None = None
    emergency_savings: float | None = None
    danger_education_done: bool = False
    bag_prepared: bool = False
    completed_pct: int = 0

    class Config:
        from_attributes = True


class BirthPrepUpdate(BaseModel):
    facility_identified: bool | None = None
    escort_identified: bool | None = None
    escort_phone: str | None = None
    transport_plan: str | None = None
    emergency_savings: float | None = None
    danger_education_done: bool | None = None
    bag_prepared: bool | None = None


class PregnancyDetailOut(PregnancyOut):
    birth_prep: BirthPrepOut | None = None
    referrals: list["ReferralOut"] = []
    care_pathway: "CarePathwayOut | None" = None


class FollowUpTaskOut(BaseModel):
    code: str
    priority: str
    title: str
    detail: str


class AncScheduleItemOut(BaseModel):
    week: int
    status: str
    estimated_due_date: date | None = None


class CarePathwayOut(BaseModel):
    trimester: str | None
    trimester_label: str
    gestation_stage: str | None
    gestation_stage_label: str
    care_flags: list[str]
    follow_up_tasks: list[FollowUpTaskOut]
    protocol_notes: list[str]
    days_since_last_visit: int | None
    mohcc_anc_weeks: list[int]
    gravida: int = 1
    parity: int = 0
    anc_schedule: list[AncScheduleItemOut] = []


class AncCalendarEntryOut(BaseModel):
    pregnancy_id: int
    patient_name: str
    ref_number: str
    weeks_pregnant: int | None
    anc_week: int
    status: str
    estimated_due_date: date | None = None
    care_flags: list[str] = []
    risk_level: str


class ComplianceCaseOut(BaseModel):
    pregnancy_id: int
    ref_number: str
    patient_name: str
    age: int | None
    weeks_pregnant: int | None
    facility_name: str
    gravida: int
    parity: int
    first_pregnancy: bool


class ComplianceDistrictOut(BaseModel):
    district: str
    pending_count: int
    cases: list[ComplianceCaseOut]


class ComplianceReportOut(BaseModel):
    total_adolescent_active: int
    guardian_consent_pending: int
    primigravida_active: int
    districts: list[ComplianceDistrictOut]


class PregnancyCreate(BaseModel):
    first_name: str
    last_name: str
    age: int
    weeks_pregnant: int
    village: str
    phone: str | None = None
    chw_id: int | None = None
    previous_cs: bool = False
    hypertension: bool = False
    multiple_gestation: bool = False
    fetal_count: int = 1
    guardian_consent_recorded: bool = False
    gravida: int = Field(default=1, ge=1)
    parity: int = Field(default=0, ge=0)
    consent_recorded: bool = True
    language: str = "en"
    whatsapp_opt_in: bool = True


class PregnancyCareUpdate(BaseModel):
    guardian_consent_recorded: bool | None = None
    multiple_gestation: bool | None = None
    fetal_count: int | None = None
    gravida: int | None = Field(default=None, ge=1)
    parity: int | None = Field(default=None, ge=0)


class DangerSignCreate(BaseModel):
    sign_type: str
    description: str | None = None


class AiInsightOut(BaseModel):
    id: int
    insight_type: str
    language: str
    content: str
    ai_powered: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None


class AiChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    preview: str | None = None

    class Config:
        from_attributes = True


class AiChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    ai_powered: bool
    message_type: str = "text"
    attachment_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AiChatResponse(BaseModel):
    reply: str
    ai_powered: bool
    message_id: int
    session_id: int


class AiTranscribeResponse(BaseModel):
    text: str


class AiAttachResponse(BaseModel):
    filename: str
    excerpt: str
    message_type: str
    suggested_message: str


class AiDashboardSummaryOut(BaseModel):
    summary: str
    highlights: list[str]
    ai_powered: bool
    generated_at: datetime


class EducationItemOut(BaseModel):
    week: int
    message: str
    due: bool


class LanguageOut(BaseModel):
    code: str
    name: str


class PregnancyStatusUpdate(BaseModel):
    status: str


class VisitOut(BaseModel):
    id: int
    pregnancy_id: int
    facility_id: int | None
    chw_id: int | None
    visit_type: str
    notes: str | None
    visited_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    detail: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class FacilityCreate(BaseModel):
    name: str
    type: str
    district: str | None = None
    phone: str | None = None


class FacilityUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    district: str | None = None
    phone: str | None = None


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    role: str
    phone: str | None = None
    facility_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    facility_id: int | None = None
    is_active: bool | None = None


class CHWCreate(BaseModel):
    name: str
    phone: str
    village: str | None = None
    facility_id: int | None = None


class CHWUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    village: str | None = None
    facility_id: int | None = None


class DistrictAnalytics(BaseModel):
    district: str
    active_pregnancies: int
    high_risk: int
    pending_referrals: int
    referrals_this_month: int
    facilities: list[dict]


class CHWOut(BaseModel):
    id: int
    name: str
    phone: str
    village: str | None
    facility_id: int | None

    class Config:
        from_attributes = True


class UssdRequest(BaseModel):
    phone: str
    text: str = ""
    session_id: str | None = None
    secret: str | None = None


class UssdResponse(BaseModel):
    response: str
    end_session: bool = False
