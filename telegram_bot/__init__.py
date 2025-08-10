
import io
import time
import pandas as pd
from telegram.ext import CommandHandler, MessageHandler, Filters

# ----- Handlers -----
def start(update, context):
    update.effective_message.reply_text("TrustMe AI bot online ✅")

def status_cmd(update, context):
    """Send a status message and attach a small CSV."""
    msg = "📊 Bot Status: OK\n• Uptime: ~{}s\n• Mode: webhook".format(int(time.time()))
    df = pd.DataFrame([{"ts": int(time.time()), "status": "ok", "notes": "sample"}])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=io.BytesIO(buf.getvalue().encode("utf-8")),
        filename="status.csv",
        caption=msg,
    )

def trades_cmd(update, context):
    """Send a few mock trades as CSV."""
    rows = [
        {"time": "2025-08-10 10:00:00", "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01, "price": 60000, "pnl": 12.5},
        {"time": "2025-08-10 11:05:00", "symbol": "ETHUSDT", "side": "SELL", "qty": 0.2, "price": 3200, "pnl": -3.2},
        {"time": "2025-08-10 12:30:00", "symbol": "SOLUSDT", "side": "BUY", "qty": 1.5, "price": 145, "pnl": 7.9},
    ]
    df = pd.DataFrame(rows)
    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=csv_bytes,
        filename="trades.csv",
        caption="📈 Sample trades (mock)",
    )

def echo(update, context):
    update.effective_message.reply_text("Got it.")

def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("status", status_cmd))
    dispatcher.add_handler(CommandHandler("trades", trades_cmd))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
