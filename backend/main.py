from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.database import Base, engine
from app.middleware.rate_limit import RateLimitMiddleware
from app.migrate import run_migrations
from app.routers import admin, api, auth, ussd, voice
from app.services.channels import build_channel_status
from app.services.scheduler import lifespan

STATIC_DIR = Path(__file__).resolve().parent / "static"

Base.metadata.create_all(bind=engine)
run_migrations()

if settings.seed_on_startup:
    from seed import seed
    seed()

app = FastAPI(
    title="SafePass API",
    description="Maternal Referral & Birth Preparedness Network — marketplace plugin",
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(api.router)
app.include_router(ussd.router)
app.include_router(voice.router)


@app.get("/health")
def health():
    channel_status = build_channel_status()
    return {
        "status": "ok",
        "service": "SafePass",
        "sms_provider": settings.sms_provider,
        "edd_reminders": settings.edd_reminder_enabled,
        "education": settings.education_enabled,
        "whatsapp": settings.whatsapp_provider,
        "voice": settings.voice_provider,
        "airtime": settings.airtime_provider,
        "ai": settings.ai_enabled,
        "rate_limit": settings.rate_limit_enabled,
        "channels": channel_status,
    }


if STATIC_DIR.exists():
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")