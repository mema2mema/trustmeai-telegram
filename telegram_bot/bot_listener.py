
import json
import logging
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from utils.log_handler import handle_log
from utils.summary_generator import generate_summary
from telegram_bot.telegram_config import TELEGRAM_TOKEN, CHAT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from TrustMe AI Telegram Bot!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Your mock balance is: 1045.78 USDT")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = generate_summary()
    await update.message.reply_text(text)

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_text = handle_log()
    await update.message.reply_text(log_text)

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Graph feature coming soon! Stay tuned.")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Withdrawal feature coming soon!")

def run_bot():
    from telegram.ext import Application
    import nest_asyncio

    nest_asyncio.apply()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("withdrawl", withdraw))

    # Detect Railway deployment
    if "RAILWAY_STATIC_URL" in os.environ:
        domain = os.environ["RAILWAY_STATIC_URL"]
        webhook_url = f"https://{domain}/webhook/{TELEGRAM_TOKEN}"
        logger.info(f"Running in Webhook mode: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            webhook_url=webhook_url,
        )
    else:
        logger.info("Running in Polling mode (local)")
        app.run_polling()
