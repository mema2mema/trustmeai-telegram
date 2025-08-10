
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

def _equity_curve(pnl: pd.Series) -> pd.Series:
    r = pd.to_numeric(pnl, errors="coerce").fillna(0.0).astype(float)
    return r.cumsum()

def _drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    dd = equity - peak
    return dd

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
        "• <b>/columns</b> — show detected columns\n"
        "• <b>/trades</b> — download current CSV\n"
        "• <b>/status</b> — current settings"
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
        update.effective_message.chat.send_action(action="upload_photo")
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=out, caption=caption)
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
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
