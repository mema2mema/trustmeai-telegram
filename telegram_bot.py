
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging

# Enable logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load token from Railway environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set public Railway URL (edit if needed)
RAILWAY_URL = "https://trustmeai-telegram-production.up.railway.app/"

# Build Telegram application
app = ApplicationBuilder().token(TOKEN).build()

# Define handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 TrustMe AI is live and listening!")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Here’s your smart summary (mock response).")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Log fetched successfully (mock response).")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Graph loaded (mock response).")

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("log", log))
app.add_handler(CommandHandler("graph", graph))

# Run webhook server
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"{RAILWAY_URL}{TOKEN}"
    )
