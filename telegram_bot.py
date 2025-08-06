
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Create the bot app
app = ApplicationBuilder().token(TOKEN).build()

# Example command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! TrustMe AI bot is live.")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Summary feature is active.")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Log feature is active.")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Graph feature is active.")

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("log", log))
app.add_handler(CommandHandler("graph", graph))

# Webhook URL from Railway
RAILWAY_URL = "https://trustmeai-telegram-production.up.railway.app/"

# Start webhook
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"{RAILWAY_URL}{TOKEN}"
    )
