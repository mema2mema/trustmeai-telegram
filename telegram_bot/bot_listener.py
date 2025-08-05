import logging
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from utils.summary_generator import generate_summary
from utils.log_handler import get_log_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_PATH = "telegram_bot/telegram_config.json"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from TrustMe AI Telegram Bot!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Your mock balance is: 1045.78 USDT")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Graph feature coming soon! Stay tuned.")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summary = generate_summary("trades/trades.csv")
    await update.message.reply_text(summary)

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_text = get_log_text()
    await update.message.reply_text(log_text)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Withdrawal request initiated. Processing...")

async def start_bot():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    app = ApplicationBuilder().token(config["bot_token"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("withdraw", withdraw))

    logger.info("✅ TrustMe AI Telegram Bot is now listening...")
    await app.run_polling()
