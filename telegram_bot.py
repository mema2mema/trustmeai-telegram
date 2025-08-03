
import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from utils.generate import generate_summary, generate_graph
from wallet import get_balance, request_withdraw

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Welcome to TrustMe AI Bot! Use /summary /log /graph /balance /withdraw")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = generate_summary()
    await update.message.reply_text(msg)

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("trade_log.csv", "rb") as f:
            await update.message.reply_document(f)
    except:
        await update.message.reply_text("No trade log found.")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    generate_graph()
    with open("equity_curve.png", "rb") as img:
        await update.message.reply_photo(img)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = get_balance()
    await update.message.reply_text(f"💰 Current Balance: ${amount:.2f}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Please specify an amount. Example: /withdraw 50")
        return
    try:
        amt = float(args[0])
        response = request_withdraw(amt)
        await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("log", log))
app.add_handler(CommandHandler("graph", graph))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("withdraw", withdraw))

app.run_webhook(
    listen="0.0.0.0",
    port=8500,
    webhook_url=WEBHOOK_URL
)
