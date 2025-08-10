
import os
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
DIGEST_FILE = "digest_chat.txt"
DIGEST_TIME_FILE = "digest_time.txt"
scheduler = BackgroundScheduler()

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

def _schedule_digest():
    from telegram import Bot
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    bot = Bot(token=token)
    scheduler.remove_all_jobs()
    if os.path.exists(DIGEST_FILE):
        if os.path.exists(DIGEST_TIME_FILE):
            t = open(DIGEST_TIME_FILE).read().strip()
            try:
                hour, minute = map(int, t.split(":"))
            except:
                hour, minute = 9, 0
        else:
            hour, minute = 9, 0
        scheduler.add_job(lambda: send_digest(bot), "cron", hour=hour, minute=minute)
    scheduler.start()

def start_scheduler():
    _schedule_digest()

def digest_cmd(update, context):
    if not context.args:
        update.message.reply_text("Usage: /digest on|off")
        return
    mode = context.args[0].lower()
    if mode == "on":
        with open(DIGEST_FILE, "w") as f:
            f.write(str(update.effective_chat.id))
        update.message.reply_text("✅ Daily digest ON")
        _schedule_digest()
    elif mode == "off":
        if os.path.exists(DIGEST_FILE):
            os.remove(DIGEST_FILE)
        update.message.reply_text("❌ Daily digest OFF")
        _schedule_digest()
    else:
        update.message.reply_text("Usage: /digest on|off")

def digesttime_cmd(update, context):
    if not context.args:
        if os.path.exists(DIGEST_TIME_FILE):
            t = open(DIGEST_TIME_FILE).read().strip()
            update.message.reply_text(f"⏰ Current digest time: {t} UTC")
        else:
            update.message.reply_text("⏰ Current digest time: 09:00 UTC (default)")
        return
    t = context.args[0]
    try:
        hour, minute = map(int, t.split(":"))
        if hour<0 or hour>23 or minute<0 or minute>59:
            raise ValueError
        with open(DIGEST_TIME_FILE, "w") as f:
            f.write(f"{hour:02d}:{minute:02d}")
        update.message.reply_text(f"✅ Digest time set to {hour:02d}:{minute:02d} UTC")
        _schedule_digest()
    except:
        update.message.reply_text("❌ Invalid time format. Use HH:MM in 24h UTC.")

def help_cmd(update, context):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Summary 7d", callback_data="HELP_SUMMARY7D")]])
    html = "<b>📘 Commands</b>\n• /digest on|off — toggle daily summary\n• /digesttime HH:MM — set daily time (UTC)\n• /summary — show stats"
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
    dp.add_handler(CommandHandler("digesttime", digesttime_cmd))
    dp.add_handler(CommandHandler("summary", summary_cmd))
    dp.add_handler(CallbackQueryHandler(on_help_buttons))
