import os
import io
from datetime import datetime
import pandas as pd
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

app = Flask(__name__)
bot = Bot(token=TOKEN) if TOKEN else None
dispatcher = Dispatcher(bot, None, workers=4, use_context=True) if bot else None

DATA_DIR = os.path.join(os.getcwd(), "data")
TRADES_CSV = os.path.join(DATA_DIR, "trades.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# Ensure CSV exists
if not os.path.exists(TRADES_CSV):
    pd.DataFrame(columns=["Type","Symbol","Entry","PnL","Time"]).to_csv(TRADES_CSV, index=False)

def _fmt_trade(type_, symbol, entry, pnl, tstamp):
    return (
        "🚀 New Trade Executed\n"
        f"Type: {type_}\n"
        f"Symbol: {symbol}\n"
        f"Entry: {entry} USDT\n"
        f"PnL: {pnl}%\n"
        f"Time: {tstamp}"
    )

def add_trade(type_, symbol, entry, pnl):
    """Append trade to CSV and push Telegram alert."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    df = pd.read_csv(TRADES_CSV)
    df.loc[len(df)] = [type_, symbol, entry, pnl, now]
    df.to_csv(TRADES_CSV, index=False)

    if bot and CHAT_ID:
        bot.send_message(chat_id=CHAT_ID, text=_fmt_trade(type_, symbol, entry, pnl, now))

# ===== Commands =====
def cmd_start(update, context):
    update.message.reply_text("✅ Bot is online. Use /help for commands.")

def cmd_help(update, context):
    update.message.reply_text(
        "Commands:\n"
        "/start – check bot\n"
        "/help – this menu\n"
        "/status – last trade + CSV link\n"
        "/trades – download current trades.csv"
    )

def cmd_status(update, context):
    try:
        df = pd.read_csv(TRADES_CSV)
        if df.empty:
            update.message.reply_text("📂 No trades yet.")
            return
        row = df.iloc[-1]
        msg = _fmt_trade(row['Type'], row['Symbol'], row['Entry'], row['PnL'], row['Time'])
        update.message.reply_text(msg)

        # attach CSV
        with open(TRADES_CSV, "rb") as f:
            context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename="trades.csv",
                                      caption="📄 Current trades.csv")

        # also share public link
        base = request.url_root.replace("http://","https://").rstrip("/")
        update.message.reply_text(f"🔗 Download: {base}/files/trades.csv")
    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}")

def cmd_trades(update, context):
    try:
        with open(TRADES_CSV, "rb") as f:
            context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename="trades.csv",
                                      caption="📄 Current trades.csv")
    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}")

# register
if dispatcher:
    dispatcher.add_handler(CommandHandler("start", cmd_start))
    dispatcher.add_handler(CommandHandler("help", cmd_help))
    dispatcher.add_handler(CommandHandler("status", cmd_status))
    dispatcher.add_handler(CommandHandler("trades", cmd_trades))
    dispatcher.add_handler(MessageHandler(Filters.text, lambda u,c: None))  # no-op to keep dispatcher alive

# ===== Flask routes =====
@app.route("/", methods=["GET"])
def health():
    if not TOKEN:
        return "❌ Missing TELEGRAM_BOT_TOKEN", 500
    return "✅ TrustMe AI Bot is running!", 200

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_any():
    if not dispatcher:
        return "Dispatcher not ready", 500
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/files/trades.csv", methods=["GET"])
def download_trades():
    if not os.path.exists(TRADES_CSV):
        return "trades.csv not found", 404
    return send_from_directory(directory=os.path.dirname(TRADES_CSV),
                               path=os.path.basename(TRADES_CSV),
                               as_attachment=True,
                               mimetype="text/csv",
                               download_name="trades.csv",
                               max_age=0)
