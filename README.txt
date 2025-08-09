# TrustMe AI Telegram — Final Backup (Production Ready)
Stable working bot with live alerts, daily summaries, wallet, CSV upload, dual webhooks.

## Railway Variables
TELEGRAM_BOT_TOKEN=your token
CHAT_ID=your chat id
SUMMARY_HOUR_UTC=8
SUMMARY_MINUTE=0

## Webhook
Accepts both `/webhook/<TOKEN>` and `/<TOKEN>`.

## Deploy
git add .
git commit -m "Final production-ready bot"
git push -u origin main

## Local
pip install -r requirements.txt
python telegram_bot/__init__.py
