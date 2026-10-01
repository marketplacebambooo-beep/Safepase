# SafePass — Africa's Talking Marketplace listing

Copy these fields into [marketplace.africastalking.dev](https://marketplace.africastalking.dev) → **Create Your Own Plugin**.

A missing logo blocks submission. Use `marketplace/logo.png`.

## Basic info

| Field | Value |
|---|---|
| Name | SafePass |
| Slug | `safepass` |
| Short description | Offline maternal referral network: CHWs on USSD, clinics and hospitals on SMS, Voice, and a web dashboard. |
| Logo | `marketplace/logo.png` |
| AT products | USSD, Bulk SMS, Voice, Airtime |
| Industry | Government, Other |
| Database | SQLite file at `/app/data/safepass.db` (persist volume `/app/data`) |
| Image | `ghcr.io/marketplacebambooo-beep/safepase:latest` (also build locally with `docker build -t safepass .`) |
| Git repo | https://github.com/marketplacebambooo-beep/Safepase |
| Port | `8001` (override with `PORT`) |
| Health | `GET /health` |

## Long description

SafePass is a marketplace plugin that any clinic, NGO, or district health team can deploy as their own isolated instance.

Community health workers register patients, check in, and report danger signs from a feature phone using USSD — no smartphone or internet required. Clinic nurses get SMS the moment a high-risk sign is reported, and Africa's Talking Voice calls them for red or emergency cases. Hospitals receive a pre-arrival SMS (and an emergency voice brief) when a referral is issued. CHWs earn small airtime rewards for completed registrations and danger-sign reports.

Each subscriber gets their own URL, database, Africa's Talking credentials, and USSD code. Languages: English, ChiShona, and isiNdebele. Optional OpenAI triage briefs fall back to rules when no API key is set.

After deploy, register these callbacks in the Africa's Talking dashboard:

- USSD: `{PUBLIC_API_URL}/ussd/callback`
- Voice: `{PUBLIC_API_URL}/voice/callback`

Demo logins (when `SEED_ON_STARTUP=true`): `chipo@mashava.clinic`, `farai@gutu.hospital`, `admin@safepass.co.zw` — password `changeme`. Change immediately.

## Environment variables

Required:

- `SECRET_KEY`
- `AT_USERNAME`
- `AT_API_KEY`
- `PUBLIC_API_URL`

Recommended:

- `SMS_SENDER_ID` (default `SAFEPASS`)
- `USSD_SERVICE_CODE` (default `*123#`)
- `AT_VOICE_PHONE`
- `AIRTIME_CURRENCY` / `AIRTIME_AMOUNT`
- `SEED_ON_STARTUP=true` for first review

Full list: `marketplace/plugin.json` and `backend/.env.example`.

## Pricing plans

1. **Starter clinic** — USD 29 / month — one clinic, USSD + SMS + dashboard
2. **District network** — USD 79 / month — Voice callbacks + CHW airtime
3. **Starter (NGN)** — NGN 15,000 / month — West Africa pricing

## Build and push

```bash
docker build -t safepass .
# Use the registry host, username, and password from the Marketplace submission form
docker tag ghcr.io/marketplacebambooo-beep/safepase:latest <at-registry>/safepass:latest
docker push <at-registry>/safepass:latest
```

Local marketplace-style run:

```bash
docker compose -f docker-compose.marketplace.yml up --build
```

App: `http://localhost:8001` · API health: `http://localhost:8001/health`
