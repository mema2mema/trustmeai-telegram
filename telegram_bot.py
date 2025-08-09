import os
from flask import Flask, request, abort
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

app = Flask(__name__)

# Read token (may be empty on import; that's OK)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Lazy init so import never fails
bot = None
dispatcher = None

def ensure_bot():
    global bot, dispatcher, TOKEN
    if TOKEN and bot is None:
        bot = Bot(token=TOKEN)
        dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, use_context=True)
        # Attach handlers once
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_cmd))

# Handlers
def start(update, context):
    update.message.reply_text("✅ TrustMe AI Bot is running! Send /help for options.")

def help_cmd(update, context):
    update.message.reply_text("Commands:\n/start – check bot\n/help – this menu")

@app.route("/", methods=["GET"])
def health():
    if not TOKEN:
        return "❌ Missing TELEGRAM_BOT_TOKEN env var", 500
    return "✅ TrustMe AI Bot is running!", 200

# Webhook endpoint that doesn't require token at import time
@app.route("/webhook/<path:token>", methods=["POST"])
def webhook(token):
    if not TOKEN or token != TOKEN:
        abort(403)
    ensure_bot()
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# Keep dev server for local runs
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
