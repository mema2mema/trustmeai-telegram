import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN env var")

app = Flask(__name__)

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, use_context=True)

def start(update, context):
    update.message.reply_text("✅ TrustMe AI Bot is running! Send /help for options.")

def help_cmd(update, context):
    update.message.reply_text("Commands:\n/start – check bot\n/help – this menu")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_cmd))

@app.route("/", methods=["GET"])
def health():
    return "✅ TrustMe AI Bot is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# Keep dev server for local runs only
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
