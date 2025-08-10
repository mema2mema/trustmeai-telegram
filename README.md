# TrustMe AI Telegram — ONECLICK v3.6.1

**What you get**
- Webhook-ready Flask app (Gunicorn)
- Commands: /start /help /status /columns /trades /log /summary /graph
- NEW: `/summary symbol=BTC timeframe=7d` filters
- PowerShell helpers in `scripts/`

## Deploy on Railway (Windows quick steps)
1. Create a Railway service and upload/unzip these files.
2. Add Variables:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - (optional) `APP_TOKEN_IN_PATH` = 1 to require `/webhook/<TOKEN>`
   - (optional) `TRADES_PATH` = trades.csv
3. After it shows **Running**, set the webhook:
   ```powershell
   cd scripts
   .\setup-webhook.ps1 -TELEGRAM_BOT_TOKEN "<YOUR_TOKEN>" -BASE "https://<your-app>.up.railway.app" -TokenInPath 0
   # If APP_TOKEN_IN_PATH=1, use -TokenInPath 1
   ```
4. Verify:
   ```powershell
   .\get-webhook-info.ps1 -TELEGRAM_BOT_TOKEN "<YOUR_TOKEN>"
   .\health.ps1 -BASE "https://<your-app>.up.railway.app"
   ```
5. Test in Telegram:
   - `/start`
   - `/columns`
   - (Send a CSV) then `/summary symbol=BTC timeframe=7d`
