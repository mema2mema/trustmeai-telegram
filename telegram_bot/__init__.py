
import io, os, traceback, re, math
import pandas as pd
import numpy as np
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Bot

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
DIGEST_FILE = "digest_chat.txt"

# ---------------- Scheduler ----------------
scheduler = BackgroundScheduler(daemon=True)

def start_scheduler():
    """Idempotent start: safe to call multiple times (e.g., per worker import)."""
    if scheduler.running:
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    bot = Bot(token=token)
    # Daily at 09:00 UTC
    scheduler.add_job(lambda: _send_digest(bot), "cron", hour=9, minute=0, id="daily_digest", replace_existing=True)
    scheduler.start()

def _send_digest(bot: Bot):
    try:
        if not os.path.exists(DIGEST_FILE):
            return
        chat_id = open(DIGEST_FILE).read().strip()
        if not chat_id:
            return
        html = _build_summary_digest()
        bot.send_message(chat_id=int(chat_id), text=html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        print("Digest send error:", e)

# --------------- CSV & detection ---------------
PROFIT_CANDIDATES = [
    "pnl","profit","pl","p&l","net_pnl","netpnl","net-profit","netprofit",
    "return","returns","roi","netp&l","gross_pnl","grosspnl","net"
]
TIME_CANDIDATES = [
    "time","timestamp","date","datetime","open_time","close_time",
    "entry_time","exit_time","created_at","closed_at","ts","opened_at"
]
SYMBOL_CANDIDATES = [
    "symbol","pair","market","ticker","instrument","asset","coin"
]

def _read_csv_safely(path: str) -> pd.DataFrame:
    for args in ({}, {"sep":";"}, {"encoding":"latin-1"}):
        try:
            return pd.read_csv(path, **args)
        except Exception:
            continue
    return pd.DataFrame()

def _auto_profit_col(df: pd.DataFrame):
    for name in PROFIT_CANDIDATES:
        for c in df.columns:
            if str(c).strip().lower() == name:
                return c
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if numeric_cols:
        var = [(c, float(pd.Series(df[c]).fillna(0).std())) for c in numeric_cols]
        var.sort(key=lambda x: x[1], reverse=True)
        return var[0][0]
    return None

def _parse_maybe_datetime(series: pd.Series) -> pd.Series:
    s = series.copy()
    if pd.api.types.is_numeric_dtype(s):
        median = float(pd.Series(s).dropna().median()) if s.notna().any() else 0.0
        unit = "ms" if median > 1e12 else "s"
        try:
            return pd.to_datetime(s, unit=unit, errors="coerce")
        except Exception:
            return pd.to_datetime(s, errors="coerce")
    return pd.to_datetime(s, errors="coerce", utc=False)

def _auto_time_col(df: pd.DataFrame):
    for name in TIME_CANDIDATES:
        for c in df.columns:
            if str(c).strip().lower() == name:
                parsed = _parse_maybe_datetime(df[c])
                if parsed.notna().sum() >= max(3, int(0.5*len(df))):
                    return c
    best = None
    best_ok = -1
    for c in df.columns:
        parsed = _parse_maybe_datetime(df[c])
        ok = parsed.notna().sum()
        if ok > best_ok:
            best_ok = ok; best = c
    if best_ok >= max(3, int(0.3*len(df))):
        return best
    return None

def _auto_symbol_col(df: pd.DataFrame):
    for name in SYMBOL_CANDIDATES:
        for c in df.columns:
            if str(c).strip().lower() == name:
                return c
    str_cols = [c for c in df.columns if df[c].dtype == object]
    best, best_score = None, -1
    for c in str_cols:
        uniq = df[c].dropna().unique()
        score = 1000 - len(uniq)
        if score > best_score:
            best, best_score = c, score
    return best

# --------------- Stats helpers ---------------
def _equity_curve(pnl: pd.Series) -> pd.Series:
    r = pd.to_numeric(pnl, errors="coerce").fillna(0.0).astype(float)
    return r.cumsum()

def _drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    dd = equity - peak
    return dd

def _max_drawdown(series: pd.Series):
    roll_max = series.cummax()
    dd = series - roll_max
    return float(dd.min())

def _streaks(bools):
    best_win, best_loss, cur, last = 0, 0, 0, None
    for v in bools:
        s = 1 if v else -1
        if last is None or s == last:
            cur += s
        else:
            cur = s
        last = s
        best_win = max(best_win, cur)
        best_loss = min(best_loss, cur)
    return best_win, -best_loss

# --------------- Formatting ---------------
def _summary_html(df: pd.DataFrame, pcol: str):
    r = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0).astype(float)
    total = int(r.shape[0])
    pnl = float(r.sum())
    win_rate = float((r > 0).mean()*100) if total else 0.0
    avg = float(r.mean()) if total else 0.0
    best = float(r.max()) if total else 0.0
    worst = float(r.min()) if total else 0.0
    wins, losses = _streaks(list(r > 0))
    mdd = _max_drawdown(r.cumsum())
    lines = [
        "Summary",
        f"Trades        : {total:>7d}",
        f"PnL           : {pnl:>7.2f}",
        f"Win rate      : {win_rate:>6.2f}%",
        f"Avg/trade     : {avg:>7.2f}",
        f"Best | Worst  : {best:>7.2f} | {worst:>7.2f}",
        f"Win/Loss strk : {wins:>3d} / {losses:>3d}",
        f"Max drawdown  : {mdd:>7.2f}",
    ]
    return "<b>📊 Performance</b>\n<pre>" + "\n".join(lines) + "</pre>"

def _build_summary_digest():
    df = _read_csv_safely(TRADES_PATH)
    if df.empty:
        return "<b>📊 Daily Digest</b>\n<pre>No trades</pre>"
    pcol = _auto_profit_col(df)
    if not pcol:
        return "<b>📊 Daily Digest</b>\n<pre>No profit column</pre>"
    block = _summary_html(df, pcol).replace("📊 Performance", "📊 Daily Digest")
    return block

# --------------- Parsing helpers ---------------
def _parse_args(args_text: str):
    out = {}
    if args_text:
        for part in re.split(r"\s+", args_text.strip()):
            if "=" in part:
                k,v = part.split("=", 1)
                out[k.strip().lower()] = v.strip()
    return out

def _apply_filters(df: pd.DataFrame, args: dict, tcol: str, scol: str):
    if "symbol" in args and scol in df.columns:
        want = args["symbol"].strip().upper()
        df = df[df[scol].astype(str).str.upper() == want]
    if "timeframe" in args and tcol in df.columns:
        tf = args["timeframe"].strip().lower()
        now = pd.Timestamp.now(tz=None)
        delta = None
        m = re.match(r"^(\d+)\s*([dhwmy])$", tf)
        if m:
            n = int(m.group(1)); unit = m.group(2)
            if unit == "d": delta = pd.Timedelta(days=n)
            elif unit == "h": delta = pd.Timedelta(hours=n)
            elif unit == "w": delta = pd.Timedelta(weeks=n)
            elif unit == "m": delta = pd.Timedelta(days=30*n)
            elif unit == "y": delta = pd.Timedelta(days=365*n)
        if delta is not None:
            cutoff = now - delta
            tvals = _parse_maybe_datetime(df[tcol])
            df = df[tvals >= cutoff]
    return df

def _parse_graph_args(args_text: str):
    mode = "equity"
    args = {}
    if args_text:
        parts = re.split(r"\s+", args_text.strip())
        for p in parts:
            if p.lower() in ("daily","dd"):
                mode = p.lower()
            elif "=" in p:
                k,v = p.split("=",1)
                args[k.strip().lower()] = v.strip()
    return mode, args

# --------------- Bot Commands ---------------
def _help_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Summary 7d", callback_data="HELP_SUMMARY7D")],
        [InlineKeyboardButton("📈 Graph Equity", callback_data="HELP_GRAPH_EQ")],
        [InlineKeyboardButton("📥 Download CSV", callback_data="HELP_TRADES")],
    ])

def start(update, context):
    html = (
        "<b>✅ Bot is online</b>\n"
        "Use <b>/help</b> for commands.\n\n"
        "<i>Send a CSV anytime to update trades.</i>"
    )
    update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def help_cmd(update, context):
    html = (
        "<b>📘 Commands</b>\n"
        "• <b>/summary</b> — detect & summarize\n"
        "    <code>/summary symbol=BTC timeframe=7d</code>\n"
        "• <b>/graph</b> — equity | daily | dd\n"
        "    <code>/graph daily</code>\n"
        "    <code>/graph dd</code>\n"
        "    <code>/graph symbol=ETH</code>\n"
        "• <b>/digest on|off</b> — toggle daily summary (09:00 UTC)\n"
        "• <b>/columns</b> — show detected columns\n"
        "• <b>/trades</b> — download current CSV\n"
        "• <b>/status</b> — current settings\n\n"
        "<i>Tip: send new CSV to replace <code>trades.csv</code>.</i>"
    )
    update.effective_message.reply_text(
        html, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=_help_keyboard()
    )

def status_cmd(update, context):
    update.effective_message.reply_text(f"TRADES_PATH: {TRADES_PATH}")

def columns_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df is None or df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
        cols = ", ".join(map(str, df.columns.tolist()))
        html = (
            "<b>🔎 Detected</b>\n"
            f"• Profit: <code>{pcol}</code>\n"
            f"• Time: <code>{tcol}</code>\n"
            f"• Symbol: <code>{scol}</code>\n\n"
            "<b>Columns</b>\n"
            f"<pre>{cols}</pre>"
        )
        update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /columns: {e}")

def trades_cmd(update, context):
    try:
        if not os.path.exists(TRADES_PATH):
            update.effective_message.reply_text("No trades file yet.")
            return
        with open(TRADES_PATH, "rb") as f:
            bio = io.BytesIO(f.read())
        bio.name = os.path.basename(TRADES_PATH)
        context.bot.send_document(chat_id=update.effective_chat.id, document=bio, filename=bio.name, caption="Current trades.csv")
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /trades: {e}")

def digest_cmd(update, context):
    try:
        if not context.args:
            update.message.reply_text("Usage: /digest on|off")
            return
        mode = context.args[0].lower()
        if mode == "on":
            with open(DIGEST_FILE, "w") as f:
                f.write(str(update.effective_chat.id))
            update.message.reply_text("✅ Daily digest ON (09:00 UTC)")
        elif mode == "off":
            if os.path.exists(DIGEST_FILE):
                os.remove(DIGEST_FILE)
            update.message.reply_text("❌ Daily digest OFF")
        else:
            update.message.reply_text("Usage: /digest on|off")
    except Exception as e:
        traceback.print_exc()
        update.message.reply_text(f"❌ Error in /digest: {e}")

def summary_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df is None or df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
        if not pcol:
            update.effective_message.reply_text("Couldn't detect profit column.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)
        df2 = _apply_filters(df.copy(), args, tcol, scol)
        if df2.empty:
            update.effective_message.reply_text("No trades after applying filters.")
            return
        html = _summary_html(df2, pcol)
        update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /summary: {e}")

def graph_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df is None or df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
        if not pcol:
            update.effective_message.reply_text("Couldn't detect profit column.")
            return

        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        mode, args = _parse_graph_args(args_txt)

        # Symbol filter (optional)
        if "symbol" in args and scol in df.columns:
            want = args["symbol"].strip().upper()
            df = df[df[scol].astype(str).str.upper() == want]

        r = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0).astype(float)

        if mode == "daily" and tcol:
            tvals = _parse_maybe_datetime(df[tcol])
            daily = r.groupby(tvals.dt.date).sum()
            fig = plt.figure(figsize=(8,4))
            plt.plot(daily.index.astype(str), daily.values)
            plt.title("Daily PnL")
            plt.xlabel("Date")
            plt.ylabel("Daily PnL")
            plt.xticks(rotation=45, ha="right")
        elif mode == "dd":
            eq = _equity_curve(r)
            dd = _drawdown(eq)
            fig = plt.figure(figsize=(8,4))
            plt.plot(dd.index.values, dd.values)
            plt.title("Drawdown")
            plt.xlabel("Trade #")
            plt.ylabel("Drawdown")
        else:
            eq = _equity_curve(r)
            fig = plt.figure(figsize=(8,4))
            plt.plot(eq.index.values, eq.values)
            plt.title("Equity Curve")
            plt.xlabel("Trade #")
            plt.ylabel("Equity")

        plt.tight_layout()
        out = io.BytesIO()
        fig.savefig(out, format="png")
        plt.close(fig)
        out.seek(0)
        out.name = "graph.png"
        caption = "Equity curve" if mode=="equity" else ("Daily PnL" if mode=="daily" else "Drawdown")
        if "symbol" in args:
            caption += f" — {args['symbol'].upper()}"
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=out, caption=caption)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /graph: {e}")

def on_help_buttons(update, context):
    try:
        q = update.callback_query
        data = q.data or ""
        q.answer()
        if data == "HELP_SUMMARY7D":
            context.args = ["timeframe=7d"]
            summary_cmd(update, context)
        elif data == "HELP_GRAPH_EQ":
            context.args = []
            graph_cmd(update, context)
        elif data == "HELP_TRADES":
            trades_cmd(update, context)
        else:
            q.edit_message_reply_markup(reply_markup=None)
    except Exception as e:
        traceback.print_exc()

def on_document(update, context):
    try:
        doc = update.message.document
        if not doc or not doc.file_name.lower().endswith(".csv"):
            update.effective_message.reply_text("Please send a CSV file.")
            return
        f = doc.get_file()
        content = f.download_as_bytearray()
        with open(TRADES_PATH, "wb") as fh:
            fh.write(content)
        update.effective_message.reply_text("✅ CSV saved. Use /summary or /graph.")
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Failed to save CSV: {e}")

def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_cmd))
    dispatcher.add_handler(CommandHandler("columns", columns_cmd))
    dispatcher.add_handler(CommandHandler("status", status_cmd))
    dispatcher.add_handler(CommandHandler("trades", trades_cmd))
    dispatcher.add_handler(CommandHandler("summary", summary_cmd))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
    dispatcher.add_handler(CommandHandler("digest", digest_cmd))
    dispatcher.add_handler(CallbackQueryHandler(on_help_buttons))
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
