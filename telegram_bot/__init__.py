import os, io, time, threading, json
from datetime import datetime, timezone
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Flask app for Gunicorn
app = Flask(__name__)

# Config
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
DATA_DIR = os.path.join(os.getcwd(), "data"); os.makedirs(DATA_DIR, exist_ok=True)
TRADES_PATHS = [os.path.join(DATA_DIR, "trades.csv"), os.path.join(os.getcwd(), "trades.csv")]
WALLET_PATH = os.path.join(DATA_DIR, "wallet.json")
SUMMARY_HOUR_UTC = int(os.environ.get("SUMMARY_HOUR_UTC", "8"))
SUMMARY_MINUTE = int(os.environ.get("SUMMARY_MINUTE", "0"))

# Telegram
bot = None
dispatcher = None
bg_started = False
last_rows = -1

def ensure_bot():
    global bot, dispatcher
    if not TOKEN:
        return False
    if bot is None:
        b = Bot(token=TOKEN)
        d = Dispatcher(bot=b, update_queue=None, workers=4, use_context=True)
        d.add_handler(CommandHandler("start", start))
        d.add_handler(CommandHandler("help", help_cmd))
        d.add_handler(CommandHandler("summary", summary_cmd))
        d.add_handler(CommandHandler("log", log_cmd))
        d.add_handler(CommandHandler("graph", graph_cmd))
        d.add_handler(CommandHandler("status", status_cmd))
        d.add_handler(CommandHandler("trades", trades_cmd))
        d.add_handler(MessageHandler(Filters.document.mime_type("text/csv"), upload_csv))
        bot = b
        dispatcher = d
    return True

def find_trades_csv():
    for p in TRADES_PATHS:
        if os.path.exists(p):
            return p
    return None

def load_trades():
    path = find_trades_csv()
    if not path:
        return None, "trades.csv not found. Upload one with a CSV file or place it in data/trades.csv."
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return None, f"Failed reading trades.csv: {e}"
    cols = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for k in ["timestamp","time","date","datetime"]:
        if k in cols:
            rename[cols[k]] = "timestamp"
            break
    pnl_col = None
    for k in ["pnl","profit","pl","p&l","profit_usd","profitusdt"]:
        if k in cols:
            pnl_col = cols[k]
            rename[pnl_col] = "pnl"
            break
    if pnl_col is None:
        return None, "CSV must include a 'pnl' column."
    df = df.rename(columns=rename)
    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            pass
    else:
        df["timestamp"] = pd.date_range(end=pd.Timestamp.utcnow(), periods=len(df), freq="T")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df, None

def equity_curve(pnls): return np.cumsum(pnls)
def max_drawdown(series):
    peaks = np.maximum.accumulate(series)
    dd = series - peaks
    return float(dd.min()) if len(series) else 0.0

def read_wallet():
    if os.path.exists(WALLET_PATH):
        try:
            return json.load(open(WALLET_PATH, "r", encoding="utf-8"))
        except Exception: pass
    return {"balance": 1000.0, "currency": "USDT"}

def write_wallet(w):
    try: json.dump(w, open(WALLET_PATH, "w", encoding="utf-8"))
    except Exception: pass

def watch_trades_loop():
    global last_rows
    while True:
        try:
            path = find_trades_csv()
            if path and ensure_bot() and CHAT_ID:
                df = pd.read_csv(path)
                rows = len(df)
                if last_rows == -1:
                    last_rows = rows
                elif rows > last_rows:
                    new = df.iloc[last_rows:]
                    wallet = read_wallet()
                    bal = float(wallet.get("balance", 0.0))
                    for _, r in new.iterrows():
                        pnl = float(pd.to_numeric(r.get("pnl", 0.0), errors="coerce") or 0.0)
                        bal += pnl
                        msg = ("📣 *Live Trade Alert*\\n"
                               f"• Symbol: *{r.get('symbol','?')}*\\n"
                               f"• Side: *{r.get('side','?')}*\\n"
                               f"• Qty: *{r.get('qty','?')}* @ *{r.get('price','?')}*\\n"
                               f"• PnL: *{pnl:.2f}*\\n"
                               f"• New Balance: *{bal:.2f} {wallet.get('currency','USDT')}*")
                        try: bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                        except Exception as e: print("send_message failed:", e)
                    wallet["balance"] = bal; write_wallet(wallet)
                    last_rows = rows
            time.sleep(5)
        except Exception as e:
            print("watch_trades_loop error:", e); time.sleep(5)

def daily_summary_loop():
    sent_day = None
    while True:
        try:
            now = datetime.now(timezone.utc)
            if now.hour == SUMMARY_HOUR_UTC and now.minute == SUMMARY_MINUTE:
                if sent_day != now.date() and ensure_bot() and CHAT_ID:
                    df, err = load_trades()
                    if not err:
                        eq = equity_curve(df["pnl"].values); mdd = max_drawdown(eq)
                        text = ("🗓️ *Daily Summary*\\n"
                                f"• Trades: *{len(df)}*\\n"
                                f"• Net PnL: *{float(df['pnl'].sum()):.2f}*\\n"
                                f"• Max DD: *{mdd:.2f}*")
                        try: bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
                        except Exception as e: print("daily send failed:", e)
                    sent_day = now.date()
            time.sleep(60)
        except Exception as e:
            print("daily_summary_loop error:", e); time.sleep(60)

def start_background_once():
    global bg_started
    if not bg_started:
        threading.Thread(target=watch_trades_loop, daemon=True).start()
        threading.Thread(target=daily_summary_loop, daemon=True).start()
        bg_started = True

# Commands
def start(update, context):
    start_background_once()
    update.message.reply_text("✅ Live alerts ON. Use /help for commands.")

def help_cmd(update, context):
    update.message.reply_text(
        "Commands:\n"
        "/start – enable background alerts\n"
        "/help – this menu\n"
        "/summary – performance summary from trades.csv\n"
        "/log – last 20 trades (sends CSV)\n"
        "/graph – equity curve image\n"
        "/status – wallet + csv status (with link)\n"
        "/trades – download current trades.csv\n"
        "Send a CSV file to update trades."
    )

def status_cmd(update, context):
    path = find_trades_csv()
    wallet = read_wallet()
    base = request.url_root.rstrip("/")  # public base URL
    csv_url = f"{base}/files/trades.csv" if path else "not found"
    msg = f"📄 CSV: {csv_url}\n💰 Balance: {wallet.get('balance',0):.2f} {wallet.get('currency','USDT')}"
    update.message.reply_text(msg)
    # attach file too
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                context.bot.send_document(chat_id=update.effective_chat.id, document=f,
                                          filename="trades.csv", caption="📄 Attached: current trades.csv")
        except Exception as e:
            update.message.reply_text(f"⚠️ Could not attach CSV: {e}")

def trades_cmd(update, context):
    path = find_trades_csv()
    if not path or not os.path.exists(path):
        update.message.reply_text("❌ trades.csv not found. Upload a CSV or place it in data/trades.csv.")
        return
    base = request.url_root.rstrip("/")
    csv_url = f"{base}/files/trades.csv"
    update.message.reply_text(f"🔗 Download: {csv_url}")
    try:
        with open(path, "rb") as f:
            context.bot.send_document(chat_id=update.effective_chat.id, document=f,
                                      filename="trades.csv", caption="📄 Current trades.csv")
    except Exception as e:
        update.message.reply_text(f"❌ Could not send CSV: {e}")

def summary_cmd(update, context):
    df, err = load_trades()
    if err: update.message.reply_text(f"❌ {err}"); return
    total = len(df); wins = int((df["pnl"]>0).sum()); win_rate = (wins/total*100) if total else 0.0
    net = float(df["pnl"].sum()); eq = equity_curve(df["pnl"].values); mdd = max_drawdown(eq)
    text = ("📈 *Summary*\n"
            f"• Trades: *{total}*\n"
            f"• Win rate: *{win_rate:.2f}%*\n"
            f"• Net PnL: *{net:.2f}*\n"
            f"• Max DD: *{mdd:.2f}*")
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='Markdown')

def log_cmd(update, context):
    df, err = load_trades()
    if err: update.message.reply_text(f"❌ {err}"); return
    tail = df.tail(20)
    bio = io.BytesIO(tail.to_csv(index=False).encode("utf-8")); bio.name = "trades_tail.csv"
    context.bot.send_document(chat_id=update.effective_chat.id, document=bio,
                              filename="trades_tail.csv", caption="Last 20 trades")

def graph_cmd(update, context):
    df, err = load_trades()
    if err: update.message.reply_text(f"❌ {err}"); return
    eq = equity_curve(df["pnl"].values)
    plt.figure(); plt.plot(df["timestamp"], eq)
    plt.title("Equity Curve"); plt.xlabel("Time"); plt.ylabel("Equity (cum PnL)"); plt.tight_layout()
    buf = io.BytesIO(); plt.savefig(buf, format="png"); plt.close(); buf.seek(0)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf, caption="📊 Equity Curve")

def upload_csv(update, context):
    try:
        file = update.message.document
        if not file.file_name.lower().endswith(".csv"):
            update.message.reply_text("❌ Please send a .csv file."); return
        fobj = context.bot.getFile(file.file_id)
        dest = TRADES_PATHS[0]; os.makedirs(os.path.dirname(dest), exist_ok=True)
        fobj.download(custom_path=dest)
        update.message.reply_text("✅ CSV uploaded. Alerts and summaries will use the new file.")
    except Exception as e:
        update.message.reply_text(f"❌ Upload failed: {e}")

# Public download route
@app.route("/files/trades.csv", methods=["GET"])
def download_trades():
    path = find_trades_csv()
    if not path or not os.path.exists(path):
        return "trades.csv not found", 404
    return send_from_directory(directory=os.path.dirname(path),
                               path=os.path.basename(path),
                               as_attachment=True,
                               download_name="trades.csv")

# Health & webhooks
@app.route("/", methods=["GET"])
def health():
    start_background_once()
    if not TOKEN: return "❌ Missing TELEGRAM_BOT_TOKEN env var", 500
    return "✅ TrustMe AI Bot is running!", 200

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_any():
    ensure_bot(); start_background_once()
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200
