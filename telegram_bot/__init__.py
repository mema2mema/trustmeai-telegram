import os, io, time, threading, json, re
from datetime import datetime, timezone
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")  # owner/admin
DATA_DIR = os.path.join(os.getcwd(), "data"); os.makedirs(DATA_DIR, exist_ok=True)
TRADES_PATHS = [os.path.join(DATA_DIR, "trades.csv"), os.path.join(os.getcwd(), "trades.csv")]
WALLET_PATH = os.path.join(DATA_DIR, "wallet.json")
TRANSFERS_PATH = os.path.join(DATA_DIR, "transfers.json")
SUMMARY_HOUR_UTC = int(os.environ.get("SUMMARY_HOUR_UTC", "8"))
SUMMARY_MINUTE = int(os.environ.get("SUMMARY_MINUTE", "0"))

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
        # commands
        d.add_handler(CommandHandler("start", start))
        d.add_handler(CommandHandler("help", help_cmd))
        d.add_handler(CommandHandler("summary", summary_cmd))
        d.add_handler(CommandHandler("log", log_cmd))
        d.add_handler(CommandHandler("graph", graph_cmd))
        d.add_handler(CommandHandler("status", status_cmd))
        d.add_handler(CommandHandler("trades", trades_cmd))
        # wallet
        d.add_handler(CommandHandler("wallet", wallet_cmd))
        d.add_handler(CommandHandler("deposit", deposit_cmd, pass_args=True))
        d.add_handler(CommandHandler("withdraw", withdraw_cmd, pass_args=True))
        d.add_handler(CommandHandler("setbalance", setbalance_cmd, pass_args=True))
        d.add_handler(CommandHandler("transfer", transfer_cmd, pass_args=True))
        d.add_handler(CommandHandler("transfers", transfers_cmd))
        # file upload
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

def read_transfers():
    if os.path.exists(TRANSFERS_PATH):
        try: return json.load(open(TRANSFERS_PATH, "r", encoding="utf-8"))
        except Exception: pass
    return []

def write_transfers(rows):
    try: json.dump(rows, open(TRANSFERS_PATH, "w", encoding="utf-8"))
    except Exception: pass

def parse_amount(s):
    try: return float(s)
    except: return None

def parse_transfer_args(args):
    # /transfer <amount> <to_chat_id>
    if not args or len(args) < 2: return None, None
    amt = parse_amount(args[0])
    to_id = args[1]
    if amt is None or amt <= 0: return None, None
    return amt, to_id

def wallet_cmd(update, context):
    w = read_wallet()
    update.message.reply_text(f"💼 Wallet: {w.get('balance',0):.2f} {w.get('currency','USDT')}")

def deposit_cmd(update, context):
    amt = parse_amount(" ".join(context.args).strip())
    if amt is None or amt <= 0:
        update.message.reply_text("Usage: /deposit <amount>")
        return
    w = read_wallet()
    w["balance"] = float(w.get("balance",0)) + amt
    write_wallet(w)
    update.message.reply_text(f"✅ Deposited {amt:.2f} {w.get('currency','USDT')}. New balance: {w['balance']:.2f}")

def withdraw_cmd(update, context):
    amt = parse_amount(" ".join(context.args).strip())
    if amt is None or amt <= 0:
        update.message.reply_text("Usage: /withdraw <amount>")
        return
    w = read_wallet()
    bal = float(w.get("balance",0))
    if amt > bal:
        update.message.reply_text(f"❌ Not enough balance. Current: {bal:.2f}")
        return
    w["balance"] = bal - amt
    write_wallet(w)
    update.message.reply_text(f"✅ Withdrew {amt:.2f} {w.get('currency','USDT')}. New balance: {w['balance']:.2f}")

def setbalance_cmd(update, context):
    if str(update.effective_user.id) != str(CHAT_ID):
        update.message.reply_text("❌ Not authorized.")
        return
    amt = parse_amount(" ".join(context.args).strip())
    if amt is None:
        update.message.reply_text("Usage: /setbalance <amount>")
        return
    w = read_wallet()
    w["balance"] = float(amt)
    write_wallet(w)
    update.message.reply_text(f"🔧 Balance set to {w['balance']:.2f} {w.get('currency','USDT')}")

def transfer_cmd(update, context):
    amt, to_id = parse_transfer_args(context.args)
    if amt is None:
        update.message.reply_text("Usage: /transfer <amount> <to_chat_id>")
        return
    w = read_wallet()
    bal = float(w.get("balance",0))
    if amt > bal:
        update.message.reply_text(f"❌ Not enough balance. Current: {bal:.2f}")
        return
    # Deduct
    w["balance"] = bal - amt; write_wallet(w)
    # Log
    rows = read_transfers()
    rows.append({"ts": datetime.utcnow().isoformat(), "from": str(update.effective_user.id), "to": str(to_id), "amount": amt})
    write_transfers(rows)
    # Notify receiver if same bot/chat reachable
    try:
        msg = f"💸 You received {amt:.2f} USDT from {update.effective_user.id}"
        Bot(token=TOKEN).send_message(chat_id=to_id, text=msg)
    except Exception as e:
        # It's fine if we can't notify (user hasn't started bot, etc.)
        pass
    update.message.reply_text(f"✅ Sent {amt:.2f} USDT to {to_id}. New balance: {w['balance']:.2f}")

def transfers_cmd(update, context):
    rows = read_transfers()
    if not rows:
        update.message.reply_text("No transfers yet.")
        return
    # show last 10
    out = ["📜 Last transfers:"]
    for r in rows[-10:]:
        out.append(f"{r['ts']}  {r['from']} ➜ {r['to']}  {r['amount']:.2f}")
    update.message.reply_text("\n".join(out))

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
                        msg = ("📣 *Live Trade Alert*\n"
                               f"• Symbol: *{r.get('symbol','?')}*\n"
                               f"• Side: *{r.get('side','?')}*\n"
                               f"• Qty: *{r.get('qty','?')}* @ *{r.get('price','?')}*\n"
                               f"• PnL: *{pnl:.2f}*\n"
                               f"• New Balance: *{bal:.2f}* USDT")
                        try: Bot(token=TOKEN).send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
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
                        text = ("🗓️ *Daily Summary*\n"
                                f"• Trades: *{len(df)}*\n"
                                f"• Net PnL: *{float(df['pnl'].sum()):.2f}*\n"
                                f"• Max DD: *{mdd:.2f}*")
                        try: Bot(token=TOKEN).send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
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

def _public_base():
    return request.url_root.replace("http://", "https://").rstrip("/")

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
        "/wallet – show wallet balance\n"
        "/deposit <amount> – add funds\n"
        "/withdraw <amount> – remove funds\n"
        "/transfer <amount> <to_chat_id> – send funds\n"
        "/transfers – show recent transfers\n"
        "Send a CSV file to update trades."
    )

def status_cmd(update, context):
    path = find_trades_csv()
    wallet = read_wallet()
    csv_url = f"{_public_base()}/files/trades.csv" if path else "not found"
    msg = f"📄 CSV: {csv_url}\n💰 Balance: {wallet.get('balance',0):.2f} {wallet.get('currency','USDT')}"
    update.message.reply_text(msg)
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
    csv_url = f"{_public_base()}/files/trades.csv"
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

@app.route("/files/trades.csv", methods=["GET"])
def download_trades():
    path = find_trades_csv()
    if not path or not os.path.exists(path):
        return "trades.csv not found", 404
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    return send_from_directory(directory=directory,
                               path=filename,
                               as_attachment=True,
                               mimetype="text/csv",
                               download_name="trades.csv",
                               max_age=0)

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
