
import io, os, traceback, re, math
from datetime import datetime, timedelta
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
    # Try default
    try:
        df = pd.read_csv(path)
        return df
    except Exception:
        pass
    # Try ; separator
    try:
        df = pd.read_csv(path, sep=";")
        return df
    except Exception:
        pass
    # Try latin-1
    try:
        df = pd.read_csv(path, encoding="latin-1")
        return df
    except Exception as e:
        raise e

def _auto_profit_col(df: pd.DataFrame):
    cols = [c for c in df.columns]
    # name priority
    for name in PROFIT_CANDIDATES:
        for c in cols:
            if str(c).strip().lower() == name:
                return c
    # numeric fallback
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if numeric_cols:
        # pick the most variable numeric column
        var = [(c, float(pd.Series(df[c]).fillna(0).std())) for c in numeric_cols]
        var.sort(key=lambda x: x[1], reverse=True)
        return var[0][0]
    return None

def _parse_maybe_datetime(series: pd.Series) -> pd.Series:
    s = series.copy()
    # numeric epoch
    if pd.api.types.is_numeric_dtype(s):
        median = float(pd.Series(s).dropna().median()) if s.notna().any() else 0.0
        unit = "ms" if median > 1e12 else "s"
        try:
            return pd.to_datetime(s, unit=unit, errors="coerce")
        except Exception:
            return pd.to_datetime(s, errors="coerce")
    # string date
    return pd.to_datetime(s, errors="coerce", utc=False)

def _auto_time_col(df: pd.DataFrame):
    cols = [c for c in df.columns]
    # named preference
    for name in TIME_CANDIDATES:
        for c in cols:
            if str(c).strip().lower() == name:
                parsed = _parse_maybe_datetime(df[c])
                if parsed.notna().sum() >= max(3, int(0.5*len(df))):
                    return c
    # try each column; pick with most parsed
    best = None
    best_ok = -1
    for c in cols:
        parsed = _parse_maybe_datetime(df[c])
        ok = parsed.notna().sum()
        if ok > best_ok:
            best_ok = ok
            best = c
    if best_ok >= max(3, int(0.3*len(df))):
        return best
    return None

def _auto_symbol_col(df: pd.DataFrame):
    cols = [c for c in df.columns]
    for name in SYMBOL_CANDIDATES:
        for c in cols:
            if str(c).strip().lower() == name:
                return c
    # Heuristic: short strings with few unique values
    str_cols = [c for c in cols if df[c].dtype == object]
    best = None
    best_score = -1
    for c in str_cols:
        uniq = df[c].dropna().unique()
        score = 1000 - len(uniq)  # fewer uniques preferred
        if score > best_score:
            best = c
            best_score = score
    return best

def _ensure_equity(df: pd.DataFrame, pcol: str):
    returns = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0).astype(float)
    equity = returns.cumsum()
    return equity

def _max_drawdown(series: pd.Series):
    roll_max = series.cummax()
    dd = series - roll_max
    mdd = dd.min()
    return float(mdd)

def _streaks(x: pd.Series):
    best_win, best_loss = 0, 0
    cur = 0
    last = None
    for v in x:
        s = 1 if v else -1
        if last is None or (s == 1 and last == 1) or (s == -1 and last == -1):
            cur += s
        else:
            cur = s
        last = s
        best_win = max(best_win, cur)
        best_loss = min(best_loss, cur)
    return best_win, -best_loss

def _parse_args(args_text: str):
    """
    Parse strings like:
      symbol=BTC timeframe=7d
      timeframe=30d
    Returns dict.
    """
    out = {}
    if not args_text:
        return out
    for part in re.split(r"\\s+", args_text.strip()):
        if "=" in part:
            k,v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out

def _apply_filters(df: pd.DataFrame, args: dict, tcol: str, scol: str):
    # Symbol filter
    if "symbol" in args and scol in df.columns:
        want = args["symbol"].strip().upper()
        df = df[df[scol].astype(str).str.upper() == want]

    # Timeframe filter: Nd, Nw, Nm, Ny, Nh
    if "timeframe" in args and tcol in df.columns:
        tf = args["timeframe"].strip().lower()
        now = pd.Timestamp.now(tz=None)
        delta = None
        m = re.match(r"^(\\d+)\\s*([dhwmy])$", tf)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit == "d":
                delta = pd.Timedelta(days=n)
            elif unit == "h":
                delta = pd.Timedelta(hours=n)
            elif unit == "w":
                delta = pd.Timedelta(weeks=n)
            elif unit == "m":
                delta = pd.Timedelta(days=30*n)
            elif unit == "y":
                delta = pd.Timedelta(days=365*n)
        if delta is not None:
            cutoff = now - delta
            tvals = _parse_maybe_datetime(df[tcol])
            df = df[tvals >= cutoff]
    return df

def _summary_text(df: pd.DataFrame, pcol: str):
    r = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0).astype(float)
    total_trades = int(r.shape[0])
    total_profit = float(r.sum())
    win_rate = float((r > 0).mean() * 100.0) if total_trades else 0.0
    avg_profit = float(r.mean()) if total_trades else 0.0
    best_trade = float(r.max()) if total_trades else 0.0
    worst_trade = float(r.min()) if total_trades else 0.0

    wins, losses = _streaks(list(r > 0))
    equity = r.cumsum()
    mdd = _max_drawdown(equity)

    lines = [
        "📊 Summary",
        f"• Trades: {total_trades}",
        f"• PnL: {total_profit:.2f}",
        f"• Win rate: {win_rate:.2f}%",
        f"• Avg/trade: {avg_profit:.2f}",
        f"• Best: {best_trade:.2f} | Worst: {worst_trade:.2f}",
        f"• Max win streak: {wins} | Max loss streak: {losses}",
        f"• Max drawdown: {mdd:.2f}",
    ]
    return "\\n".join(lines)

def start(update, context):
    update.effective_message.reply_text(
        "TrustMe AI Bot is live ✅\\n"
        "Send a CSV or use /help"
    )

def help_cmd(update, context):
    update.effective_message.reply_text(
        "Commands:\\n"
        "/status — show settings\\n"
        "/columns — detect time & profit columns\\n"
        "/trades — download current CSV\\n"
        "/summary [symbol=BTC] [timeframe=7d]\\n"
        "/graph — equity curve"
    )

def status_cmd(update, context):
    update.effective_message.reply_text(
        f"TRADES_PATH: {TRADES_PATH}"
    )

def columns_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df is None or df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df)
        tcol = _auto_time_col(df)
        scol = _auto_symbol_col(df)
        cols = ", ".join(map(str, df.columns.tolist()))
        update.effective_message.reply_text(
            f"Detected profit: {pcol}\\nDetected time: {tcol}\\nDetected symbol: {scol}\\n\\nColumns: {cols}"
        )
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
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=bio,
            filename=bio.name
        )
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
        pcol = _auto_profit_col(df)
        tcol = _auto_time_col(df)
        scol = _auto_symbol_col(df)
        if not pcol:
            update.effective_message.reply_text("Couldn't detect profit column.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)

        # Filters
        df_filtered = df.copy()
        df_filtered = _apply_filters(df_filtered, args, tcol, scol)

        if df_filtered.empty:
            update.effective_message.reply_text("No trades after applying filters.")
            return

        text = _summary_text(df_filtered, pcol)
        update.effective_message.reply_text(text)
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
        update.effective_message.reply_text(f"✅ Saved CSV to {TRADES_PATH}. Use /summary or /graph.")
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
