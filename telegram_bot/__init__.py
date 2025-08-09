# telegram_bot/__init__.py
# Unified Flask app with Telegram handlers and webhook routes.
import os
import io
from flask import Flask, request, abort
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Create the Flask app that Gunicorn will import via wsgi:app
app = Flask(__name__)

# Read token (don't crash if missing so the app can at least boot)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Optional CSV locations
CANDIDATE_PATHS = [
    os.path.join(os.getcwd(), "trades.csv"),
    os.path.join(os.getcwd(), "data", "trades.csv"),
]

# Lazy-init Telegram dispatcher so import never fails if envvar missing
bot = None
dispatcher = None

def ensure_bot():
    """Ensure PTB Bot + Dispatcher exist before processing an update."""
    global bot, dispatcher
    if not TOKEN:
        return False
    if bot is None:
        b = Bot(token=TOKEN)
        d = Dispatcher(bot=b, update_queue=None, workers=0, use_context=True)
        # Register command handlers
        d.add_handler(CommandHandler("start", start))
        d.add_handler(CommandHandler("help", help_cmd))
        d.add_handler(CommandHandler("summary", summary_cmd))
        d.add_handler(CommandHandler("log", log_cmd))
        d.add_handler(CommandHandler("graph", graph_cmd))
        bot = b
        dispatcher = d
    return True

# ---------- Helpers for /summary,/log,/graph ----------
def find_trades_csv():
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            return p
    return None

def load_trades():
    path = find_trades_csv()
    if not path:
        return None, "trades.csv not found. Place it at repo root or in data/trades.csv."
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return None, f"Failed to read trades.csv: {e}"
    cols = {c.lower().strip(): c for c in df.columns}
    rename_map = {}
    # Timestamp
    ts_col = None
    for k in ["timestamp","time","date","datetime"]:
        if k in cols:
            ts_col = cols[k]; rename_map[ts_col] = "timestamp"; break
    # PnL
    pnl_col = None
    for k in ["pnl","profit","pl","p&l"]:
        if k in cols:
            pnl_col = cols[k]; rename_map[pnl_col] = "pnl"; break
    if pnl_col is None:
        return None, "trades.csv must include a 'pnl' column."
    df = df.rename(columns=rename_map)
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

def equity_curve(pnls):
    return np.cumsum(pnls)

def max_drawdown(series):
    peaks = np.maximum.accumulate(series)
    drawdowns = (series - peaks)
    return float(drawdowns.min()) if len(series) else 0.0

def summary_text(df):
    total_trades = int(len(df))
    wins = int((df["pnl"] > 0).sum())
    losses = int((df["pnl"] <= 0).sum())
    win_rate = (wins / total_trades * 100.0) if total_trades else 0.0
    gross_profit = float(df.loc[df["pnl"] > 0, "pnl"].sum())
    gross_loss = float(df.loc[df["pnl"] <= 0, "pnl"].sum())
    net_pnl = float(df["pnl"].sum())
    avg_pnl = float(df["pnl"].mean()) if total_trades else 0.0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else float("inf") if gross_profit>0 else 0.0
    eq = equity_curve(df["pnl"].values)
    mdd = max_drawdown(eq)
    return "\n".join([
        "📈 *TrustMe AI – Performance Summary*",
        f"• Trades: *{total_trades}*",
        f"• Wins / Losses: *{wins}* / *{losses}*",
        f"• Win rate: *{win_rate:.2f}%*",
        f"• Net PnL: *{net_pnl:.2f}*",
        f"• Avg PnL / trade: *{avg_pnl:.4f}*",
        f"• Profit Factor: *{profit_factor:.2f}*",
        f"• Max Drawdown: *{mdd:.2f}*",
    ])

# ---------- Telegram command handlers ----------
def start(update, context):
    update.message.reply_text("✅ TrustMe AI Bot is running! Commands: /help /summary /log /graph")

def help_cmd(update, context):
    update.message.reply_text(
        "Commands:\n"
        "/start – health check\n"
        "/help – this menu\n"
        "/summary – performance summary from trades.csv\n"
        "/log – last 20 trades (sends CSV)\n"
        "/graph – equity curve image"
    )

def summary_cmd(update, context):
    df, err = load_trades()
    if err:
        update.message.reply_text(f"❌ {err}"); return
    context.bot.send_message(chat_id=update.effective_chat.id, text=summary_text(df), parse_mode='Markdown')

def log_cmd(update, context):
    df, err = load_trades()
    if err:
        update.message.reply_text(f"❌ {err}"); return
    tail = df.tail(20)
    csv_bytes = tail.to_csv(index=False).encode("utf-8")
    bio = io.BytesIO(csv_bytes); bio.name = "trades_tail.csv"
    context.bot.send_document(chat_id=update.effective_chat.id, document=bio, filename="trades_tail.csv", caption="Last 20 trades")

def graph_cmd(update, context):
    df, err = load_trades()
    if err:
        update.message.reply_text(f"❌ {err}"); return
    eq = equity_curve(df["pnl"].values)
    import matplotlib.pyplot as plt
    plt.figure(); plt.plot(df["timestamp"], eq); plt.title("Equity Curve"); plt.xlabel("Time"); plt.ylabel("Equity (cum PnL)"); plt.tight_layout()
    buf = io.BytesIO(); plt.savefig(buf, format="png"); plt.close(); buf.seek(0)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf, caption="📊 Equity Curve")

# ---------- Flask routes ----------
@app.route("/", methods=["GET"])
def health():
    if not TOKEN:
        return "❌ Missing TELEGRAM_BOT_TOKEN env var", 500
    return "✅ TrustMe AI Bot is running!", 200

# Accept both /webhook/<TOKEN> (new) and /<TOKEN> (legacy)
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_any():
    if not ensure_bot():
        abort(500)
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200
