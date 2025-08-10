# TrustMe AI Telegram Bot (Final Pack)

### What’s inside
- Webhook-ready Flask app + Gunicorn (Dockerfile)
- CSV download route: `/files/trades.csv`
- Commands: `/start`, `/help`, `/status`, `/trades`
- Helper `add_trade()` to append a trade & push Telegram alert
- `test_trade.py` to send a sample trade alert
- `.env.example` — copy to `.env` and fill token + chat id

### Deploy (Railway)
1) Unzip into your repo folder and overwrite files.
2) Commit & push:
   ```bash
   git add .
   git commit -m "Final production-ready bot"
   git push -u origin main
   ```
3) Set variables in Railway → **Variables**:
   - `TELEGRAM_BOT_TOKEN`
   - `CHAT_ID`
4) Set webhook (PowerShell):
   ```powershell
   $TOKEN = "<YOUR_TOKEN>"
   $BASE  = "<YOUR_RAILWAY_BASE_URL>"  # e.g. https://your-app.up.railway.app
   Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/deleteWebhook" -Method Post
   Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook/$TOKEN" }
   ```

### Local test
1) Copy `.env.example` to `.env` and fill values.
2) Install deps: `pip install -r requirements.txt`
3) Run: `python wsgi.py`
4) In another terminal: `python test_trade.py` (sends a sample trade alert)
