
import io, os, traceback, re, math
import pandas as pd
import numpy as np
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram import ParseMode

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")

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
    raise RuntimeError("Failed to read CSV")

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
        m = re.match(r"^(\\d+)\\s*([dhwmy])$", tf)
        if m:
            n = int(m.group(1)); unit = m.group(2)
            delta = {"d":pd.Timedelta(days=n),
                     "h":pd.Timedelta(hours=n),
                     "w":pd.Timedelta(weeks=n),
                     "m":pd.Timedelta(days=30*n),
                     "y":pd.Timedelta(days=365*n)}.get(unit)
        if delta is not None:
            cutoff = now - delta
            tvals = _parse_maybe_datetime(df[tcol])
            df = df[tvals >= cutoff]
    return df

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
        "• <b>/start</b> — check bot\n"
        "• <b>/help</b> — this menu\n"
        "• <b>/summary</b> — auto-detect columns &amp; summarize\n"
        "    <code>/summary symbol=BTC timeframe=7d</code>\n"
        "• <b>/graph</b> — equity curve image\n"
        "• <b>/status</b> — current settings\n"
        "• <b>/trades</b> — download current CSV\n"
        "• <b>/columns</b> — show detected columns\n\n"
        "<i>Tip: send new CSV to replace <code>trades.csv</code>.</i>"
    )
    update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

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

def log_cmd(update, context):
    return columns_cmd(update, context)

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
        pcol = _auto_profit_col(df)
        if not pcol:
            update.effective_message.reply_text("Couldn't detect profit column.")
            return
        r = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0).astype(float)
        eq = r.cumsum()
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
        out.name = "equity.png"
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=out, caption="Equity curve")
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /graph: {e}")

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
    dispatcher.add_handler(CommandHandler("log", log_cmd))
    dispatcher.add_handler(CommandHandler("summary", summary_cmd))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
