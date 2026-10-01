# SafePass — Maternal Referral & Birth Preparedness Network

Marketplace-ready platform coordinating maternal care from CHW (USSD) → clinic nurse → hospital with live SMS, Voice, WhatsApp, and Airtime via Africa's Talking.

Repo: [github.com/marketplacebambooo-beep/Safepase](https://github.com/marketplacebambooo-beep/Safepase)

## Architecture

| Layer | Technology |
|-------|------------|
| CHW field workers | USSD `*123#` via Africa's Talking |
| Clinic / Hospital | React web dashboard |
| SMS / WhatsApp | Africa's Talking Bulk SMS + WhatsApp |
| Voice | Africa's Talking outbound calls for red/emergency events |
| Airtime | Africa's Talking CHW rewards for registrations and danger-sign reports |
| API | FastAPI 2.2.0 + SQLAlchemy (SQLite by default) |

## First-time setup

### 1. Backend

```bash
cd safepass/backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set SECRET_KEY, AT_USERNAME, AT_API_KEY, AT_VOICE_PHONE, etc.
```

For initial facilities and staff accounts:

```bash
# In .env set SEED_ON_STARTUP=true, then:
python seed.py
# Default password: changeme — change immediately
```

Or run the API once with `SEED_ON_STARTUP=true`, then set it back to `false`.

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend

```bash
cd safepass/frontend
npm install
npm run dev
```

Dev server: `http://localhost:5173` (use `--port 5174` if 5173 is already taken). Vite proxies `/api`, `/ussd`, `/voice`, and `/health` to the API on port 8001.

For production, set `VITE_API_URL` to your API origin and build:

```bash
VITE_API_URL=https://api.yourdomain.com npm run build
```

The marketplace Docker image builds the frontend into the API container, so `VITE_API_URL` can stay empty (same origin).

## Live SMS, USSD, Voice & Airtime — physical phone

Use the **live** account at [account.africastalking.com](https://account.africastalking.com). Sandbox and the web simulator do **not** work on real handsets.

### Checklist

| Step | Action |
|------|--------|
| 1 | Create **Team** + **App** on live AT → note `AT_USERNAME` |
| 2 | **Settings → API Key** → generate → paste into `.env` as `AT_API_KEY` |
| 3 | Email **support@africastalking.com** (template: `backend/at_live_request_email.txt`) — request USSD code, SAFEPASS sender ID, Voice number, phone whitelist |
| 4 | Expose API on **HTTPS** (`ngrok http 8001` or deploy) → set `PUBLIC_API_URL` |
| 5 | AT dashboard → **USSD** → callback `{PUBLIC_API_URL}/ussd/callback` |
| 6 | AT dashboard → **Voice** → callback `{PUBLIC_API_URL}/voice/callback` and set `AT_VOICE_PHONE` |
| 7 | Register CHW handset: `python register_chw_phone.py +26377xxxxxxx` |
| 8 | Test SMS: `python test_live_at.py +26377xxxxxxx` |
| 9 | Dial assigned `USSD_SERVICE_CODE` from physical phone |

### .env (live)

```
AT_USERNAME=your_live_app_username
AT_API_KEY=atsk_live_key_here
SMS_SENDER_ID=SAFEPASS
AT_VOICE_PHONE=+26377xxxxxxx
PUBLIC_API_URL=https://your-https-url
USSD_SERVICE_CODE=*assigned-code#
AIRTIME_CURRENCY=USD
AIRTIME_AMOUNT=0.20
```

Restart backend after changes. Check **Channel Log** in the app for SMS, WhatsApp, Voice, and Airtime status.

## Workflows

1. **CHW registers patient** via USSD `*123#` → option 1 (includes risk factors) → optional airtime reward
2. **CHW check-in** via USSD option 2 → persisted as visits, clinic notified
3. **CHW reports danger sign** via USSD option 3 → clinic nurses receive SMS; red/emergency also triggers a Voice call; CHW may receive airtime
4. **Nurse registers patient** via web dashboard → Register Patient (consent stored)
5. **Nurse records danger signs** on patient detail → risk recalculated
6. **Nurse completes birth prep** including escort phone → checklist tracked
7. **Nurse issues referral** → hospital staff + patient receive SMS; emergency/high-risk also Voice-calls the hospital
8. **Hospital updates status** (including cancel/no-show) → validated state machine
9. **Hospital views patient** from referral card → read-only patient summary
10. **Admin manages** facilities, users, CHWs, district analytics

## Default logins (after `python seed.py`)

| Role | Email | Password |
|------|-------|----------|
| Clinic nurse | `chipo@mashava.clinic` | `changeme` |
| Hospital | `farai@gutu.hospital` | `changeme` |
| Admin | `admin@safepass.co.zw` | `changeme` |

## Docker

```bash
cd safepass
docker compose up --build
```

API: `http://localhost:8001` · Web: `http://localhost:5173`

### Marketplace image (single container)

One image serves the API, USSD/Voice callbacks, and the built dashboard. This is the image to push to the Africa's Talking Container registry.

```bash
docker compose -f docker-compose.marketplace.yml up --build
```

Published image (built on every push to `master`):

```bash
docker pull ghcr.io/marketplacebambooo-beep/safepase:latest
docker run --rm -p 8001:8001 --env-file backend/.env ghcr.io/marketplacebambooo-beep/safepase:latest
```

App: `http://localhost:8001` · Health: `http://localhost:8001/health`

Listing copy, env contract, pricing, and logo: `marketplace/MARKETPLACE.md`. Idea-form pitch: `marketplace/HACKATHON_IDEA.md`.

### Production (nginx + built frontend)

```bash
cd safepass
# Set SECRET_KEY, SMS credentials, CORS_ORIGINS in .env
docker compose -f docker-compose.prod.yml up --build -d
```

Serves on port **80** with nginx proxying `/api`, `/ussd`, `/voice`, and `/health` to the backend.

## EDD SMS reminders

Automatic reminders are sent to patients (and clinic nurses) when EDD is **7 days**, **1 day**, or **today** away. Runs on startup and every 6 hours (configurable via `EDD_REMINDER_INTERVAL_HOURS`).

Admins can trigger manually: `POST /api/admin/run-edd-reminders`

## Multilingual & WhatsApp education

- **Languages:** English, ChiShona, isiNdebele — USSD option 5, clinic registration, and all patient messages
- **WhatsApp:** Weekly education tips + alerts sent alongside SMS when `whatsapp_opt_in` is enabled
- **Education milestones:** Weeks 12, 20, 28, 32, 36, 38, 40 — auto-sent by background job

Configure in `.env`:
```
WHATSAPP_PROVIDER=log          # or africas_talking
EDUCATION_ENABLED=true
```

## Voice emergencies and CHW airtime

When risk is **red** or **emergency**, SafePass places an Africa's Talking Voice call that reads a spoken brief to clinic nurses (CHW danger-sign reports) or hospital staff (emergency referrals). Register `{PUBLIC_API_URL}/voice/callback` as the Voice callback.

CHWs receive a small airtime reward after a successful USSD registration or danger-sign report (`AIRTIME_CURRENCY` + `AIRTIME_AMOUNT`). Rewards are de-duplicated per CHW, reason, and pregnancy.

Set `VOICE_PROVIDER=log` and `AIRTIME_PROVIDER=log` to keep these on the notification log without live AT calls.

## AI features

SafePass uses AI (optional OpenAI API) with **rule-based fallback** when no API key is set:

| AI use case | When it runs |
|---|---|
| **Danger sign triage** | CHW USSD report or nurse web entry → urgency brief for clinic |
| **Referral pre-arrival brief** | Nurse issues referral → hospital gets AI summary SMS |
| **Global AI assistant** | All staff roles — free-text chat in natural language (OpenAI + fallback) |
| **Education messaging** | Scheduled multilingual tips by gestational week (not LLM-generated) |

Set `OPENAI_API_KEY` in `.env` for live AI; demo works without it.

## Rate limiting

Login and USSD endpoints are limited to 20 requests per minute per IP (configurable). Disable with `RATE_LIMIT_ENABLED=false`.

## Tests

```bash
cd safepass/backend
python -m pytest tests/ -v
```

Tests force `SMS_PROVIDER`, `WHATSAPP_PROVIDER`, `VOICE_PROVIDER`, and `AIRTIME_PROVIDER` to `log` so they never call live Africa's Talking.

## API health

`GET /health` returns service status plus SMS, WhatsApp, Voice, and Airtime channel state.
