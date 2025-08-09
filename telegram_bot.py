import os
from flask import Flask, request, abort
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# Flask app exported at module top-level for Gunicorn
app = Flask(__name__)

# Token can be missing at import-time; we don't crash
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Lazy-init PTB so import never fails
bot = None
dispatcher = None

def ensure_bot():
    global bot, dispatcher
    if not TOKEN:
        return False
    if bot is None:
        b = Bot(token=TOKEN)
        d = Dispatcher(bot=b, update_queue=None, workers=0, use_context=True)
        # Handlers
        d.add_handler(CommandHandler("start", start))
        d.add_handler(CommandHandler("help", help_cmd))
        # Publish
        globals()["bot"] = b
        globals()["dispatcher"] = d
    return True

# --- Handlers ---
def start(update, context):
    update.message.reply_text("✅ TrustMe AI Bot is running! Send /help for options.")

def help_cmd(update, context):
    update.message.reply_text("Commands:\n/start – check bot\n/help – this menu")

# --- Routes ---
@app.route("/", methods=["GET"])
def health():
    if not TOKEN:
        return "❌ Missing TELEGRAM_BOT_TOKEN env var", 500
    return "✅ TrustMe AI Bot is running!", 200

# Webhook endpoint that does not require token at import
@app.route("/webhook/<path:token>", methods=["POST"])
def webhook(token):
    if not TOKEN or token != TOKEN:
        abort(403)
    if not ensure_bot():
        abort(500)
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# Local dev server (not used on Railway)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
