from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./safepass.db"
    access_token_expire_minutes: int = 480

    # Only seed when explicitly enabled (first deploy / dev)
    seed_on_startup: bool = False

    # SMS: "africas_talking" (live) — set AT_USERNAME + AT_API_KEY
    sms_provider: str = "africas_talking"
    at_username: str = ""
    at_api_key: str = ""
    sms_sender_id: str = "SAFEPASS"

    # WhatsApp education — "africas_talking" (live)
    whatsapp_provider: str = "africas_talking"
    whatsapp_sender_id: str = "SAFEPASS"

    # Voice emergency callbacks — "africas_talking" or "log"
    voice_provider: str = "africas_talking"
    voice_enabled: bool = True
    at_voice_phone: str = ""

    # Airtime CHW incentives — "africas_talking" or "log"
    airtime_provider: str = "africas_talking"
    airtime_enabled: bool = True
    airtime_currency: str = "USD"
    airtime_amount: str = "0.20"

    # Public API base URL for USSD callback registration (no trailing slash)
    # e.g. https://api.safepass.co.zw or https://your-ngrok-url.ngrok-free.app
    public_api_url: str = ""

    # USSD short code shown in admin/setup (e.g. *384*123#)
    ussd_service_code: str = "*123#"

    # AI triage & briefs — optional OpenAI-compatible API
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ai_enabled: bool = True

    # Weekly education job
    education_enabled: bool = True

    # USSD gateway security (optional — reject unsigned callbacks when set)
    ussd_callback_secret: str = ""

    # Comma-separated origins, e.g. https://app.safepass.co.zw
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # EDD SMS reminders — background job runs every N hours
    edd_reminder_enabled: bool = True
    edd_reminder_interval_hours: int = 6
    follow_up_reminder_enabled: bool = True

    # Rate limiting on login and USSD endpoints
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 20

    class Config:
        env_file = ".env"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
