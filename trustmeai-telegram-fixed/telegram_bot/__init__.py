
import io
import os
import time
import traceback
import pandas as pd
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram import ParseMode

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
SAMPLE_TRADES = "sample_trades.csv"

_WALLETS = {}

def _get_wallet(chat_id):
    w = _WALLETS.get(chat_id, {"balance": 0.0})
    _WALLETS[chat_id] = w
    return w

def _ensure_sample_if_missing():
    if not os.path.exists(TRADES_PATH):
        if os.path.exists(SAMPLE_TRADES):
            return SAMPLE_TRADES
    return TRADES_PATH if os.path.exists(TRADES_PATH) else None

def _load_df_safely():
    path = _ensure_sample_if_missing()
    if not path:
        return None, None
    try:
        df = pd.read_csv(path)
        if "time" in df.columns:
            try:
                df["time"] = pd.to_datetime(df["time"])
            except Exception:
                pass
        return df, path
    except Exception:
        traceback.print_exc()
        return None, path

def _equity_curve_png_bytes(df):
    try:
        pnl = df["pnl"] if "pnl" in df.columns else None
        if pnl is None or len(pnl) == 0:
            return None
        equity = pnl.cumsum()
        x = df["time"] if "time" in df.columns else range(len(equity))
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(x, equity)
        ax.set_title("Equity Curve")
        ax.set_xlabel("Time")
        ax.set_ylabel("Cumulative PnL")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        traceback.print_exc()
        return None

def start(update, context):
    update.effective_message.reply_text("✅ Bot is online. Use /help for commands.")

def help_cmd(update, context):
    text = (
        "Commands:\n"
        "/start – check bot\n"
        "/help – this menu\n"
        "/summary – performance summary from trades.csv\n"
        "/graph – equity curve image\n"
        "/status – last trade + CSV link\n"
        "/trades – download current trades.csv\n"
        "Send a CSV file to update trades.\n"
    )
    update.effective_message.reply_text(text)

def status_cmd(update, context):
    df, path = _load_df_safely()
    if df is None or df.empty:
        update.effective_message.reply_text("🟡 No trades yet. Upload a CSV or use /trades to get the sample file.")
        return
    buf = io.StringIO()
    df.tail(20).to_csv(buf, index=False)
    buf.seek(0)
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=io.BytesIO(buf.getvalue().encode("utf-8")),
        filename="status.csv",
        caption="📊 Status: latest rows attached."
    )

def trades_cmd(update, context):
    df, path = _load_df_safely()
    if df is None:
        update.effective_message.reply_text("🟡 No trades file found yet. Send a CSV to set trades.")
        return
    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=csv_bytes,
        filename="trades.csv",
        caption="📈 Current trades.csv"
    )

def log_cmd(update, context):
    return trades_cmd(update, context)

def summary_cmd(update, context):
    df, path = _load_df_safely()
    if df is None or df.empty or "pnl" not in df.columns:
        update.effective_message.reply_text("🟡 No trades with 'pnl' column found. Upload a CSV with a 'pnl' column.")
        return
    total = len(df)
    wins = int((df["pnl"] > 0).sum())
    losses = int((df["pnl"] <= 0).sum())
    win_rate = (wins/total*100.0) if total else 0.0
    gross = float(df["pnl"].sum())
    avg = float(df["pnl"].mean())
    equity = df["pnl"].cumsum()
    peak = equity.cummax()
    drawdown = equity - peak
    mdd = float(drawdown.min())
    text = (
        "📜 Summary\n"
        f"• Trades: {total}\n"
        f"• Wins/Losses: {wins}/{losses}\n"
        f"• Win Rate: {win_rate:.2f}%\n"
        f"• Gross PnL: {gross:.2f}\n"
        f"• Avg PnL/Trade: {avg:.2f}\n"
        f"• Max Drawdown: {mdd:.2f}\n"
    )
    update.effective_message.reply_text(text)

def graph_cmd(update, context):
    df, path = _load_df_safely()
    if df is None or df.empty or "pnl" not in df.columns:
        update.effective_message.reply_text("🟡 Can't plot. Upload a CSV with a 'pnl' column.")
        return
    img = _equity_curve_png_bytes(df)
    if not img:
        update.effective_message.reply_text("🟡 Failed to build graph. Check your CSV data.")
        return
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=img, caption="📈 Equity Curve")

def on_document(update, context):
    try:
        doc = update.message.document
        if not doc or not doc.file_name.lower().endswith(".csv"):
            return update.effective_message.reply_text("Please upload a .csv file.")
        file = context.bot.getFile(doc.file_id)
        b = file.download_as_bytearray()
        with open(TRADES_PATH, "wb") as f:
            f.write(b)
        update.effective_message.reply_text(f"✅ Received and saved `{doc.file_name}` as `{TRADES_PATH}`.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        update.effective_message.reply_text(f"❌ Failed to save CSV: {e}")

def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_cmd))
    dispatcher.add_handler(CommandHandler("status", status_cmd))
    dispatcher.add_handler(CommandHandler("trades", trades_cmd))
    dispatcher.add_handler(CommandHandler("log", log_cmd))
    dispatcher.add_handler(CommandHandler("summary", summary_cmd))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
