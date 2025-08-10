
import os
from telegram import Bot

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # your chat id
if not TOKEN or not CHAT_ID:
    raise SystemExit("Set TOKEN and CHAT_ID env vars")

bot = Bot(TOKEN)
bot.send_message(chat_id=CHAT_ID, text="🚀 Test alert from TrustMe AI")
print("Sent")
