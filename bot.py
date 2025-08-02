
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler  # ✅ ADD THIS

# Load .env
load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Your existing bot code...



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello from TrustMe AI Telegram Bot!")

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=CHAT_ID, text="🚀 TrustMe AI bot is deployed and running!")

def scheduled_job():
    print("Running scheduled task...")
    # Example: send scheduled updates to Telegram

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("notify", notify))

if __name__ == "__main__":
    print("Bot started...")
    scheduler = BackgroundScheduler()
    scheduler.start()
    app.run_polling()
