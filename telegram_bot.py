
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from utils import generate_summary, generate_graph
from wallet import get_balance, request_withdraw

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Welcome to TrustMe AI! Use /summary, /log, /graph, /balance, or /withdraw")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = generate_summary()
    await update.message.reply_text(msg)

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("trade_log.csv"):
        await update.message.reply_document(document=open("trade_log.csv", "rb"))
    else:
        await update.message.reply_text("❌ No trade log available.")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    generate_graph()
    await update.message.reply_photo(photo=open("equity_curve.png", "rb"))

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = get_balance()
    await update.message.reply_text(f"💰 Current Balance: ${bal:.2f}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = request_withdraw()
    await update.message.reply_text(result)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("log", log))
app.add_handler(CommandHandler("graph", graph))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("withdraw", withdraw))
app.run_polling()
