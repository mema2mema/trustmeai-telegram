
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

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("TrustMe AI bot is live! ✅")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Summary generated.")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Trade log retrieved.")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Graph is on the way.")

# Register command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("log", log))
app.add_handler(CommandHandler("graph", graph))

# Hardcoded Railway HTTPS webhook URL
RAILWAY_URL = "https://trustmeai-telegram-production.up.railway.app/"

# Start webhook
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=RAILWAY_URL + TOKEN
    )
