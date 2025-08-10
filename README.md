
# TrustMe AI Telegram Bot (Railway Webhook)

This package is ready to deploy on Railway and includes:
- Flask webhook server (`wsgi.py`)
- PTB v13 handlers (`telegram_bot/__init__.py`)
- `/status` attaches a CSV; `/trades` sends trades.csv
- Procfile for Gunicorn

## 1) Setup env vars (Railway)
- `TELEGRAM_BOT_TOKEN` = your Telegram bot token (keep secret)
- Optional: `CHAT_ID` for test script

## 2) Deploy
Push to Railway (or connect repo). Ensure `Procfile` is detected.

## 3) Set webhook
PowerShell example:
```powershell
$TOKEN = "<NEW_BOT_TOKEN>"
$BASE  = "https://<your-railway-subdomain>.up.railway.app"
iwr -Uri "https://api.telegram.org/bot$TOKEN/deleteWebhook" -Method Post
iwr -Uri "https://api.telegram.org/bot$TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook/$TOKEN" }
iwr -Uri "https://api.telegram.org/bot$TOKEN/getWebhookInfo"
```

## 4) Test in Telegram
Send `/start`, then `/status`, then `/trades` in your chat.

## 5) Local run (optional)
```
pip install -r requirements.txt
set TOKEN=<YOUR_TOKEN>  # Windows CMD
# or $env:TOKEN="<YOUR_TOKEN>" in PowerShell
python wsgi.py
```
Telegram won't reach localhost unless you use ngrok and set the webhook to that URL.
