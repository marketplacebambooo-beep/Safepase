# Hackathon idea submission

Use this text in the Africa's Talking idea form.

## Project name

SafePass — Maternal Referral & Birth Preparedness Network

## One-line pitch

A marketplace-ready maternal referral network that works on `*123#`: CHWs report danger signs over USSD, clinics get SMS, and hospitals get a Voice pre-arrival brief — even when there is no internet.

## Problem

Most maternal deaths in rural Africa happen on the journey between a village, a clinic, and a hospital. Community health workers have feature phones, not smartphones. Clinics cannot see danger signs in time. Hospitals learn about a referral when the patient is already at the gate. Customer-support-style call centers and web-only tools do not reach the last mile.

## Solution

SafePass is a reusable Africa's Talking plugin, not a one-clinic demo.

- **USSD** — CHWs register patients, check in, and report bleeding, headache, swelling, or reduced movement without data.
- **Bulk SMS** — clinic nurses, hospital staff, patients, and escorts get live alerts, EDD reminders, and education tips.
- **Voice** — red/emergency danger signs and emergency referrals trigger an outbound call that reads a spoken brief.
- **Airtime** — CHWs receive a small airtime reward for each completed registration or danger-sign report, so the channel pays for itself.
- **Web dashboard** — nurses, hospitals, and admins manage referrals, birth prep, and district analytics when they do have connectivity.

Any clinic, NGO, or ministry can deploy their own isolated instance from the Africa's Talking Marketplace.

## Africa's Talking APIs used

| API | What it does in SafePass |
|---|---|
| USSD | Offline CHW workflow (`/ussd/callback`) |
| Bulk SMS | Staff and patient notifications |
| Voice | Emergency spoken briefs (`/voice/callback`) |
| Airtime | CHW incentives for completed field actions |

## Who it is for

- District health teams and ministries (Government)
- Faith-based and NGO clinic networks
- Telecom-powered health programmes that need a deployable plugin, not a custom build

## Why it fits this hackathon

- Improves access where internet is weak (USSD-first)
- Combines multiple AT channels into one service-delivery platform
- Is packaged as a marketplace plugin: Docker image, env contract, pricing, logo, isolated instances
- Addresses a real African service-delivery failure, not a toy callback

## Demo path (5 minutes)

1. Open the deployed instance and sign in as `chipo@mashava.clinic` / `changeme`
2. Dial or simulate USSD: register a patient, then report bleeding
3. Show the Channel Log: SMS to the clinic, Voice call queued, Airtime reward to the CHW
4. Issue an emergency referral and show the hospital Voice + SMS pre-arrival brief
5. Show Marketplace packaging: `Dockerfile`, `marketplace/plugin.json`, env vars, pricing

## Team / contact

Fill with your names, emails, Slack handles, and GitHub URL before submitting the form.

## Links to fill on the form

- Marketplace: https://marketplace.africastalking.dev
- Idea form: use the event's "Hackathon idea submission form"
- Gig/portfolio form: only if you want AT to send paid work
- Slack: Africa's Talking community
