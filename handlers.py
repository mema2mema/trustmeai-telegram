
from telegram.ext import CommandHandler

def columns_cmd(update, context):
    try:
        df, path = _load_df_safely()
        if df is None or df.empty:
            update.effective_message.reply_text("No CSV loaded. Send a CSV first.")
            return

        pcol = df.attrs.get("profit_col")
        tcol = df.attrs.get("time_col")

        cols = list(map(str, df.columns.tolist()))
        total = len(cols)

        preview = ", ".join(cols[:40]) + (" ..." if total > 40 else "")
        msg = (
            f"CSV: {path}\n"
            f"Detected profit: {pcol}\n"
            f"Detected time: {tcol}\n"
            f"Columns ({total}): {preview}\n"
            "(Full list attached if too long)"
        )

        update.effective_message.reply_text(msg)

        if total > 40:
            import io
            body = (
                f"CSV: {path}\n"
                f"Detected profit: {pcol}\n"
                f"Detected time: {tcol}\n\n"
                f"All columns ({total}):\n" + "\n".join(cols)
            )
            bio = io.BytesIO(body.encode("utf-8"))
            bio.name = "columns.txt"
            context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=bio,
                filename="columns.txt",
                caption="Full columns list"
            )

    except Exception as e:
        update.effective_message.reply_text(f"Error in /columns: {e}")
