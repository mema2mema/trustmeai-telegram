# TrustMe AI — Telegram Bot (Compatibility Build)

This build accepts either:
- `BOT_TOKEN` **or** `TELEGRAM_BOT_TOKEN`
- `PUBLIC_URL` **or** `WEBHOOK_URL`

## Env vars (Railway → Variables)
Set **one** of each pair:
- `BOT_TOKEN` **or** `TELEGRAM_BOT_TOKEN`
- `PUBLIC_URL` **or** `WEBHOOK_URL`
And also set:
- `WEBHOOK_SECRET`
- `ADMIN_PASS`

## Start
- Local: `cp .env.example .env`, `npm i`, `npm start`
- Railway: add vars, deploy, open `/admin`, click **Start Bot**
