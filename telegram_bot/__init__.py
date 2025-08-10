
import io, os, traceback, re, math
import pandas as pd
import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc as TZ_UTC
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Bot

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRADES_PATH = os.environ.get("TRADES_PATH", "trades.csv")
DIGEST_FILE = "digest_chat.txt"
DIGEST_TIME_FILE = "digest_time.txt"

# ---------------- Scheduler (UTC) ----------------
scheduler = BackgroundScheduler(daemon=True, timezone=TZ_UTC)

def start_scheduler():
    if scheduler.running:
        return
    _schedule_digest()
    scheduler.start()

def _schedule_digest():
    try:
        for job in scheduler.get_jobs():
            scheduler.remove_job(job.id)
    except Exception:
        pass
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or not os.path.exists(DIGEST_FILE):
        return
    chat_id = open(DIGEST_FILE).read().strip()
    if not chat_id:
        return
    hour, minute = 9, 0
    if os.path.exists(DIGEST_TIME_FILE):
        try:
            t = open(DIGEST_TIME_FILE).read().strip()
            h, m = map(int, t.split(":"))
            if 0 <= h <= 23 and 0 <= m <= 59:
                hour, minute = h, m
        except Exception:
            pass
    bot = Bot(token=token)
    scheduler.add_job(lambda: _send_digest(bot, chat_id),
                      trigger='cron', hour=hour, minute=minute,
                      id='daily_digest', replace_existing=True, timezone=TZ_UTC)

def _send_digest(bot: Bot, chat_id: str):
    try:
        html = _build_summary_digest()
        bot.send_message(chat_id=int(chat_id), text=html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        print("Digest send error:", e)

# ---------------- CSV helpers ----------------
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
    pattern = re.compile(r"(symbol|pair|market|ticker|instrument|asset|coin)", re.IGNORECASE)
    for c in df.columns:
        if pattern.search(str(c)):
            return c
    candidates = []
    for c in df.columns:
        s = df[c]
        if s.dtype == object:
            uniq = s.dropna().astype(str).str.upper().unique()
            if 1 < len(uniq) < max(50, len(s)//2):
                candidates.append((c, len(uniq)))
    if candidates:
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    return None

# ---------------- Stats & formatting ----------------
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

# ---------------- Parsers & filters ----------------
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

# ---------------- New commands: perfs & heatmap ----------------
def _perfs_table(df: pd.DataFrame, pcol: str, scol: str, top: int = 15) -> str:
    g = df.groupby(scol)[pcol]
    total = g.count()
    pnl = g.sum()
    avg = g.mean()
    win = df.assign(win=lambda x: (pd.to_numeric(x[pcol], errors="coerce") > 0).astype(int)).groupby(scol)['win'].mean()*100.0
    out = pd.DataFrame({"Trades": total, "PnL": pnl, "Win%": win, "Avg": avg}).fillna(0.0)
    out = out.sort_values("PnL", ascending=False).head(top)
    # Build monospaced table
    lines = ["Symbol Performance"]
    lines.append(f"{'Symbol':<10} {'Trades':>6} {'PnL':>10} {'Win%':>7} {'Avg':>9}")
    for idx, r in out.iterrows():
        lines.append(f"{str(idx)[:10]:<10} {int(r['Trades']):>6d} {float(r['PnL']):>10.2f} {float(r['Win%']):>6.2f}% {float(r['Avg']):>9.2f}")
    return "<b>📈 Per-Symbol</b>\n<pre>" + "\n".join(lines) + "</pre>"

def perfs_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
        if not (pcol and scol):
            update.effective_message.reply_text("Need profit and symbol columns.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)
        df2 = _apply_filters(df.copy(), args, tcol, scol)
        if df2.empty:
            update.effective_message.reply_text("No trades after applying filters.")
            return
        html = _perfs_table(df2, pcol, scol, top=int(args.get("top", 15)))
        update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /perfs: {e}")

def heatmap_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
        if not (pcol and tcol):
            update.effective_message.reply_text("Need profit and time columns.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)
        df2 = _apply_filters(df.copy(), args, tcol, scol)

        # Build daily pnl and pivot by date x symbol (or weekday if arg 'weekday=1')
        tvals = _parse_maybe_datetime(df2[tcol])
        df2 = df2.assign(__date=tvals.dt.date)
        if 'weekday' in args and args['weekday'] in ('1','true','yes'):
            df2 = df2.assign(__weekday=tvals.dt.day_name())
            pivot = df2.pivot_table(index="__weekday", columns=scol if scol in df2.columns else "__date",
                                    values=pcol, aggfunc="sum", fill_value=0.0)
            ylabel = "Weekday"
            xlabel = "Symbol" if scol in df2.columns else "Date"
        else:
            pivot = df2.pivot_table(index="__date", columns=scol if scol in df2.columns else "__date",
                                    values=pcol, aggfunc="sum", fill_value=0.0)
            ylabel = "Date"
            xlabel = "Symbol" if scol in df2.columns else "Date"

        if pivot.empty:
            update.effective_message.reply_text("No data for heatmap.")
            return

        fig = plt.figure(figsize=(8,5))
        plt.imshow(pivot.values, aspect='auto')
        plt.title("PnL Heatmap")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        out = io.BytesIO()
        fig.savefig(out, format="png")
        plt.close(fig)
        out.seek(0)
        out.name = "heatmap.png"
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=out, caption="PnL Heatmap")
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /heatmap: {e}")

# ---------------- Existing UI ----------------
def _help_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Summary 7d", callback_data="HELP_SUMMARY7D")],
        [InlineKeyboardButton("📈 Graph Equity", callback_data="HELP_GRAPH_EQ")],
        [InlineKeyboardButton("📥 Download CSV", callback_data="HELP_TRADES")],
    ])

def _help_html():
    return (
        "<b>📘 Commands</b>\n"
        "• <b>/summary</b> — detect & summarize\n"
        "    <code>/summary symbol=BTC timeframe=7d</code>\n"
        "• <b>/perfs</b> — per-symbol table (add <code>top=10</code>)\n"
        "• <b>/graph</b> — equity | daily | dd\n"
        "    <code>/graph daily</code>\n"
        "    <code>/graph dd</code>\n"
        "    <code>/graph symbol=ETH</code>\n"
        "• <b>/heatmap</b> — PnL heatmap (add <code>weekday=1</code>)\n"
        "• <b>/digest on|off</b> — toggle daily summary\n"
        "• <b>/digesttime HH:MM</b> — set daily time (UTC)\n"
        "• <b>/digeststatus</b> — show current state\n"
        "• <b>/columns</b> — show detected columns\n"
        "• <b>/trades</b> — download current CSV\n"
        "• <b>/status</b> — current settings\n\n"
        "<i>Tip: send new CSV to replace <code>trades.csv</code>.</i>"
    )

def start(update, context):
    banner = "<b>✅ Bot is online</b>\nUse <b>/help</b> for commands.\n\n<i>Send a CSV anytime to update trades.</i>"
    update.effective_message.reply_text(banner, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    update.effective_message.reply_text(_help_html(), parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=_help_keyboard())

def help_cmd(update, context):
    update.effective_message.reply_text(_help_html(), parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=_help_keyboard())

# digest suite (reuse from 3.9.4)
def digeststatus_cmd(update, context):
    on = os.path.exists(DIGEST_FILE) and (open(DIGEST_FILE).read().strip() != "")
    t = "09:00"
    if os.path.exists(DIGEST_TIME_FILE):
        t = open(DIGEST_TIME_FILE).read().strip() or t
    update.message.reply_text(f"📣 Digest: {'ON' if on else 'OFF'} | ⏰ Time: {t} UTC")

def digest_cmd(update, context):
    try:
        arg = " ".join(context.args).strip().lower() if context.args else ""
        arg = re.sub(r"[^a-z0-9: ]+", "", arg)
        if arg in ("on","enable","start","1","true"):
            with open(DIGEST_FILE, "w") as f:
                f.write(str(update.effective_chat.id))
            _schedule_digest()
            t = "09:00"
            if os.path.exists(DIGEST_TIME_FILE):
                t = open(DIGEST_TIME_FILE).read().strip() or t
            update.message.reply_text(f"✅ Daily digest ON (time {t} UTC)")
            return
        if arg in ("off","disable","stop","0","false"):
            if os.path.exists(DIGEST_FILE):
                os.remove(DIGEST_FILE)
            _schedule_digest()
            update.message.reply_text("❌ Daily digest OFF")
            return
        digeststatus_cmd(update, context)
        update.message.reply_text("Usage: /digest on|off")
    except Exception as e:
        traceback.print_exc()
        update.message.reply_text(f"❌ Error in /digest: {e}")

def digesttime_cmd(update, context):
    if not context.args:
        t = "09:00"
        if os.path.exists(DIGEST_TIME_FILE):
            t = open(DIGEST_TIME_FILE).read().strip() or t
        update.message.reply_text(f"⏰ Current digest time: {t} UTC")
        return
    t = context.args[0]
    try:
        h, m = map(int, t.split(":"))
        if h<0 or h>23 or m<0 or m>59:
            raise ValueError
        with open(DIGEST_TIME_FILE, "w") as f:
            f.write(f"{h:02d}:{m:02d}")
        _schedule_digest()
        update.message.reply_text(f"✅ Digest time set to {h:02d}:{m:02d} UTC")
    except Exception:
        update.message.reply_text("❌ Invalid time format. Use HH:MM (24h UTC).")

# columns/trades/summary/graph from 3.9.4
def status_cmd(update, context):
    update.effective_message.reply_text(f"TRADES_PATH: {TRADES_PATH}")

def columns_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df.empty:
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

def _summary_html_public(df):
    pcol = _auto_profit_col(df)
    return _summary_html(df, pcol) if pcol else "No profit column."

def _parse_graph_args(args_text: str):
    mode = "equity"
    args = {}
    if args_text:
        parts = re.split(r"\\s+", args_text.strip())
        for p in parts:
            if p.lower() in ("daily","dd"):
                mode = p.lower()
            elif "=" in p:
                k,v = p.split("=",1)
                args[k.strip().lower()] = v.strip()
    return mode, args

def _apply_filters_public(df, args):
    pcol = _auto_profit_col(df); tcol = _auto_time_col(df); scol = _auto_symbol_col(df)
    return _apply_filters(df, args, tcol, scol), pcol, tcol, scol

def summary_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)
        df2, pcol, tcol, scol = _apply_filters_public(df.copy(), args)
        if df2.empty:
            update.effective_message.reply_text("No trades after applying filters.")
            return
        html = _summary_html_public(df2)
        update.effective_message.reply_text(html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        traceback.print_exc()
        update.effective_message.reply_text(f"❌ Error in /summary: {e}")

def graph_cmd(update, context):
    try:
        df = _read_csv_safely(TRADES_PATH)
        if df.empty:
            update.effective_message.reply_text("No CSV loaded.")
            return
        args_txt = " ".join(context.args) if getattr(context, "args", None) else ""
        args = _parse_args(args_txt)
        df2, pcol, tcol, scol = _apply_filters_public(df.copy(), args)
        if not pcol:
            update.effective_message.reply_text("Couldn't detect profit column.")
            return
        r = pd.to_numeric(df2[pcol], errors="coerce").fillna(0.0).astype(float)

        mode = "equity"
        if args_txt:
            for token in re.split(r"\\s+", args_txt.strip()):
                if token.lower() in ("daily","dd"):
                    mode = token.lower()

        if mode == "daily" and tcol:
            tvals = _parse_maybe_datetime(df2[tcol])
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

# callbacks & upload
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
    dispatcher.add_handler(CommandHandler("summary", summary_cmd))
    dispatcher.add_handler(CommandHandler("perfs", perfs_cmd))
    dispatcher.add_handler(CommandHandler("graph", graph_cmd))
    dispatcher.add_handler(CommandHandler("heatmap", heatmap_cmd))
    dispatcher.add_handler(CommandHandler("columns", columns_cmd))
    dispatcher.add_handler(CommandHandler("trades", trades_cmd))
    dispatcher.add_handler(CommandHandler("status", status_cmd))
    dispatcher.add_handler(CommandHandler("digest", digest_cmd))
    dispatcher.add_handler(CommandHandler("digesttime", digesttime_cmd))
    dispatcher.add_handler(CommandHandler("digeststatus", digeststatus_cmd))
    dispatcher.add_handler(CallbackQueryHandler(on_help_buttons))
    dispatcher.add_handler(MessageHandler(Filters.document, on_document))
