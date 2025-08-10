
import io, os, traceback, re
import pandas as pd
import numpy as np
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
DIGEST_FILE = "digest_chat.txt"
scheduler = BackgroundScheduler()

# --- CSV Helpers ---
def read_csv():
    try:
        return pd.read_csv(TRADES_PATH)
    except Exception:
        return pd.DataFrame()

def detect_profit_col(df):
    candidates = ["pnl","profit","pl","net","return"]
    for c in df.columns:
        if str(c).strip().lower() in candidates:
            return c
    return None

# --- Summary ---
def build_summary():
    df = read_csv()
    if df.empty:
        return "No trades."
    pcol = detect_profit_col(df)
    if not pcol:
        return "No profit column."
    r = pd.to_numeric(df[pcol], errors="coerce").fillna(0)
    lines = [
        "Summary",
        f"Trades : {len(r)}",
        f"PnL    : {r.sum():.2f}",
        f"Win%   : {(r>0).mean()*100:.2f}%",
        f"Avg    : {r.mean():.2f}",
    ]
    return "<b>📊 Daily Digest</b>\n<pre>" + "\n".join(lines) + "</pre>"

# --- Digest Job ---
def send_digest(bot):
    try:
        if not os.path.exists(DIGEST_FILE):
            return
        chat_id = open(DIGEST_FILE).read().strip()
        if not chat_id:
            return
        bot.send_message(chat_id=chat_id, text=build_summary(), parse_mode=ParseMode.HTML)
    except Exception as e:
        print("Digest send error:", e)

def start_scheduler():
    from telegram import Bot
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    bot = Bot(token=token)
    scheduler.add_job(lambda: send_digest(bot), "cron", hour=9, minute=0)  # 9 AM UTC
    scheduler.start()

# --- Commands ---
def digest_cmd(update, context):
    if not context.args:
        update.message.reply_text("Usage: /digest on|off")
        return
    mode = context.args[0].lower()
    if mode == "on":
        with open(DIGEST_FILE, "w") as f:
            f.write(str(update.effective_chat.id))
        update.message.reply_text("✅ Daily digest ON (9 AM UTC)")
    elif mode == "off":
        if os.path.exists(DIGEST_FILE):
            os.remove(DIGEST_FILE)
        update.message.reply_text("❌ Daily digest OFF")
    else:
        update.message.reply_text("Usage: /digest on|off")

def help_cmd(update, context):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Summary 7d", callback_data="HELP_SUMMARY7D")]])
    html = "<b>📘 Commands</b>\n• /digest on|off — toggle daily summary\n• /summary — show stats"
    update.message.reply_text(html, parse_mode=ParseMode.HTML, reply_markup=kb)

def summary_cmd(update, context):
    update.message.reply_text(build_summary(), parse_mode=ParseMode.HTML)

def on_help_buttons(update, context):
    query = update.callback_query
    if query.data == "HELP_SUMMARY7D":
        summary_cmd(update, context)
    query.answer()

def register_handlers(dp):
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("digest", digest_cmd))
    dp.add_handler(CommandHandler("summary", summary_cmd))
    dp.add_handler(CallbackQueryHandler(on_help_buttons))
