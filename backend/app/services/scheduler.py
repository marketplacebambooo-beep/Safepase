import asyncio
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import SessionLocal
from app.services.channels import build_channel_status
from app.services.edd_reminders import run_edd_reminders
from app.services.education import run_weekly_education
from app.services.follow_up_scheduler import run_follow_up_reminders

logger = logging.getLogger(__name__)


async def _background_jobs_loop():
    while True:
        db = SessionLocal()
        try:
            if settings.edd_reminder_enabled:
                result = run_edd_reminders(db)
                logger.info("EDD reminder job: %s", result)
            if settings.education_enabled:
                result = run_weekly_education(db)
                logger.info("Education job: %s", result)
            if settings.follow_up_reminder_enabled:
                result = run_follow_up_reminders(db)
                logger.info("Follow-up pathway job: %s", result)
        except Exception:
            logger.exception("Background job failed")
        finally:
            db.close()
        await asyncio.sleep(settings.edd_reminder_interval_hours * 3600)


@asynccontextmanager
async def lifespan(app):
    status = build_channel_status()
    if status["issues"]:
        for issue in status["issues"]:
            logger.warning("Channel setup: %s", issue)
    if status["ussd_callback_url"]:
        logger.info("USSD callback URL: %s", status["ussd_callback_url"])
    if status["credentials_configured"]:
        logger.info("Africa's Talking credentials loaded for user: %s", settings.at_username)

    task = None
    if settings.edd_reminder_enabled or settings.education_enabled or settings.follow_up_reminder_enabled:
        db = SessionLocal()
        try:
            if settings.edd_reminder_enabled:
                logger.info("EDD startup: %s", run_edd_reminders(db))
            if settings.education_enabled:
                logger.info("Education startup: %s", run_weekly_education(db))
            if settings.follow_up_reminder_enabled:
                logger.info("Follow-up startup: %s", run_follow_up_reminders(db))
        finally:
            db.close()
        task = asyncio.create_task(_background_jobs_loop())
        logger.info("Background scheduler started (every %sh)", settings.edd_reminder_interval_hours)
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
