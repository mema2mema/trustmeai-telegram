
# TrustMe AI Telegram Bot — Fixed Build
- Robust /summary, /log, /graph
- CSV upload to set trades
- Uses sample_trades.csv if no trades.csv yet

Env:
- TELEGRAM_BOT_TOKEN=<token>
- APP_TOKEN_IN_PATH=0
- TRADES_PATH=trades.csv (optional)

Webhook (without token in path):
iwr -Uri "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" -Method Post -Body @{ url = "https://<your-app>.up.railway.app/webhook" }
