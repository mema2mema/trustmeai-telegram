
import io, os, time, traceback, re
import pandas as pd
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram import ParseMode

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
SAMPLE_TRADES = "sample_trades.csv"

# ------- Column detection -------
PROFIT_CANDIDATES = [
    "pnl","profit","pl","p&l","net_pnl","netpnl","net-profit","netprofit",
    "return","returns","roi","netp&l","gross_pnl","grosspnl"
]
TIME_CANDIDATES = [
    "time","timestamp","date","datetime","open_time","close_time","trade_time"
]

def _normalize(name: str):
    return re.sub(r"[^a-z0-9]", "", name.lower())

def detect_columns(df):
    cols_norm = {c: _normalize(c) for c in df.columns}
    inv = {v: k for k,v in cols_norm.items()}
    # profit
    profit_col = None
    for cand in PROFIT_CANDIDATES:
        key = _normalize(cand)
        if key in inv:
            profit_col = inv[key]
            break
    # try fuzzy: any column containing these tokens
    if profit_col is None:
        for c, n in cols_norm.items():
            if any(tok in n for tok in ["pnl","profit","pl","ret","roi"]):
                profit_col = c
                break
    # time
    time_col = None
    for cand in TIME_CANDIDATES:
        key = _normalize(cand)
        if key in inv:
            time_col = inv[key]
            break
    if time_col is None:
        for c, n in cols_norm.items():
            if any(tok in n for tok in ["time","date"]):
                time_col = c
                break
    return profit_col, time_col

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
        # convert potential comma decimal to dot for numeric columns
        for c in df.columns:
            if df[c].dtype == object:
                try:
                    df[c] = df[c].str.replace(",", ".").astype(float)
                except Exception:
                    pass
        # detect columns
        pcol, tcol = detect_columns(df)
        if tcol:
            try:
                df[tcol] = pd.to_datetime(df[tcol])
            except Exception:
                pass
        df.attrs["profit_col"] = pcol
        df.attrs["time_col"] = tcol
        df.attrs["path"] = path
        return df, path
    except Exception:
        traceback.print_exc()
        return None, path

def _equity_curve_png_bytes(df):
    pcol = df.attrs.get("profit_col")
    if not pcol or pcol not in df.columns or df[pcol].dropna().empty:
        return None
    equity = df[pcol].fillna(0).cumsum()
    xcol = df.attrs.get("time_col")
    x = df[xcol] if xcol and xcol in df.columns else range(len(equity))
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(x, equity)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Time" if xcol else "Trade #")
    ax.set_ylabel("Cumulative Profit")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf

# ---------- Commands ----------
def start(update, context):
    update.effective_message.reply_text("✅ Bot is online. Use /help for commands.")

def help_cmd(update, context):
    text = (
        "Commands:\n"
        "/start – check bot\n"
        "/help – this menu\n"
        "/summary – performance summary (auto-detect profit/time columns)\n"
        "/graph – equity curve image\n"
        "/status – last trades + CSV\n"
        "/trades – download current CSV\n"
        "/columns – show detected columns\n"
        "Send a CSV to update trades.\n"
    )
    update.effective_message.reply_text(text)

def columns_cmd(update, context):
    df, path = _load_df_safely()
    if df is None or df.empty:
        update.effective_message.reply_text("No CSV loaded. Send a CSV first.")
        return
    pcol = df.attrs.get("profit_col")
    tcol = df.attrs.get("time_col")
    cols = ", ".join(df.columns)
    update.effective_message.reply_text(
        f"CSV: `{path}`\nColumns: {cols}\nDetected profit: `{pcol}`\nDetected time: `{tcol}`",
        parse_mode=ParseMode.MARKDOWN
    )

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
    b = io.BytesIO()
    df.to_csv(b, index=False)
    b.seek(0)
    context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=b,
        filename="trades.csv",
        caption="📈 Current trades.csv"
    )

def log_cmd(update, context):
    return trades_cmd(update, context)

def summary_cmd(update, context):
    try:
        df, path = _load_df_safely()
        if df is None or df.empty:
            update.effective_message.reply_text("🟡 No data loaded. Send a CSV first.")
            return
        pcol = df.attrs.get("profit_col")
        if not pcol:
            update.effective_message.reply_text("🟡 Could not detect profit column. Use names like 'pnl', 'profit', 'pl', 'return'.")
            return
        series = pd.to_numeric(df[pcol], errors="coerce").fillna(0)
        total = len(series)
        wins = int((series > 0).sum())
        losses = total - wins
        win_rate = (wins/total*100.0) if total else 0.0
        gross = float(series.sum())
        avg = float(series.mean())
        equity = series.cumsum()
        peak = equity.cummax()
        drawdown = equity - peak
        mdd = float(drawdown.min())
        text = (
            "📜 Summary\n"
            f"• Source: `{path}`\n"
            f"• Profit column: `{pcol}`\n"
            f"• Trades: {total}\n"
            f"• Wins/Losses: {wins}/{losses}\n"
            f"• Win Rate: {win_rate:.2f}%\n"
            f"• Gross: {gross:.4f}\n"
            f"• Avg/trade: {avg:.4f}\n"
            f"• Max Drawdown: {mdd:.4f}\n"
        )
        update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ /summary failed: {e}")

def graph_cmd(update, context):
    try:
        df, path = _load_df_safely()
        if df is None or df.empty:
            update.effective_message.reply_text("🟡 No data loaded. Send a CSV first.")
            return
        img = _equity_curve_png_bytes(df)
        if not img:
            update.effective_message.reply_text("🟡 Couldn't build graph. Make sure your CSV has a profit column like pnl/profit/pl/return.")
            return
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=img, caption="📈 Equity Curve")
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ /graph failed: {e}")

def on_document(update, context):
    try:
        doc = update.message.document
        if not doc or not doc.file_name.lower().endswith(".csv"):
            return update.effective_message.reply_text("Please upload a .csv file.")
        file = context.bot.getFile(doc.file_id)
        b = file.download_as_bytearray()
        with open(TRADES_PATH, "wb") as f:
            f.write(b)
        update.effective_message.reply_text(f"✅ Saved `{doc.file_name}` as `{TRADES_PATH}`.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Failed to save CSV: {e}")

def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_cmd))
    dispatcher.add_handler(CommandHandler("columns", columns_cmd))
    dispatcher.add_handler(CommandHandler("status", status_cmd))
    dispatcher.add_handler(CommandHandler("trades", trades_cmd))
    dispatcher.add_handler(CommandHandler("log", log_cmd))
    dispatcher.add_handler(CommandHandler("summary", summary_cmd))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
