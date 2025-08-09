# TrustMe AI Telegram (Railway, Gunicorn)

## Files
- Dockerfile (Gunicorn production)
- requirements.txt
- telegram_bot.py (safe import, webhook at /webhook/<TOKEN>)

## Railway Variables
- TELEGRAM_BOT_TOKEN = <your token>

## Set webhook (PowerShell)
$TOKEN = "<YOUR_NEW_TELEGRAM_BOT_TOKEN>"
$BASE  = "https://trustmeai-telegram-production.up.railway.app"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/deleteWebhook" -Method Post
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook/$TOKEN" }

## VS Code push (example)
git add .
git commit -m "Production: Gunicorn + safe webhook endpoint"
git push
