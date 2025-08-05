# telegram_bot/bot_listener.py

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pandas as pd
import os

# Load config
import json
with open("telegram_bot/telegram_config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRADES_PATH = "trades/trades.csv"

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from TrustMe AI Telegram Bot!")

# /summary
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = pd.read_csv(TRADES_PATH)
        total_profit = df['profit'].sum()
        total_trades = len(df)
        reply = f"📊 Trade Summary:\n\nTotal Trades: {total_trades}\nTotal Profit: {total_profit:.2f} USDT"
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("⚠️ Error reading trade summary.")
        logger.error(e)

# /log
async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = pd.read_csv(TRADES_PATH)
        last_rows = df.tail(5).to_string(index=False)
        await update.message.reply_text(f"🧾 Last 5 Trades:\n\n{last_rows}")
    except Exception as e:
        await update.message.reply_text("⚠️ Couldn't load trade log.")
        logger.error(e)

# /balance (mock version)
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Your mock balance is: 1045.78 USDT")

# /graph (mock placeholder)
async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Graph feature coming soon! Stay tuned.")

# Main bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("graph", graph))

    print("✅ TrustMe AI Telegram Bot is now listening...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio

    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())