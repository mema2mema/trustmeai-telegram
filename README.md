
# TrustMe AI Telegram Bot — ONECLICK

Guaranteed /webhook route + auto-detect CSV columns + full commands.

## Railway
1) Variables:
   - TELEGRAM_BOT_TOKEN = <your token>
   - APP_TOKEN_IN_PATH = 0
2) Deploy this ZIP.
3) Set webhook:
   $TOKEN="<your token>"
   $BASE="https://<your-app>.up.railway.app"
   iwr -Uri "https://api.telegram.org/bot$TOKEN/deleteWebhook" -Method Post
   iwr -Uri "https://api.telegram.org/bot$TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook" }
