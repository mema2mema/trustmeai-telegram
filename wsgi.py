
import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher
from telegram.utils.request import Request

from telegram_bot import register_handlers

# ---- ENV ----
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
APP_TOKEN_IN_PATH = os.environ.get("APP_TOKEN_IN_PATH", "1") == "1"

MISSING_TOKEN = TOKEN is None

# ---- Flask ----
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    if MISSING_TOKEN:
        return (
            "<h1>TrustMe AI Telegram Bot is running ⚠️</h1>"
            "<p><b>Warning:</b> TELEGRAM_BOT_TOKEN is not set. "
            "Set it in Railway Variables and redeploy.</p>",
            200,
        )
    return "<h1>TrustMe AI Telegram Bot is running ✅</h1><p>Use /health for status.</p>", 200

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

# ---- Bot/Dispatcher (webhook mode) ----
if MISSING_TOKEN:
    bot = None
    dispatcher = None
    print("[wsgi] WARNING: TELEGRAM_BOT_TOKEN not set. Bot not initialized.")
else:
    request_obj = Request(con_pool_size=8)
    bot = Bot(token=TOKEN, request=request_obj)
    dispatcher = Dispatcher(bot, None, workers=2, use_context=True)
    register_handlers(dispatcher)
    print("[wsgi] Dispatcher ready with workers=2")

def _process_update_common():
    if MISSING_TOKEN:
        return jsonify({"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}), 503
    try:
        payload = request.get_json(force=True)
        print("[webhook] Incoming update:", payload)
        update = Update.de_json(payload, bot)
        dispatcher.process_update(update)
    except Exception as e:
        print("[webhook] Error:", repr(e))
        return jsonify({"ok": False, "error": str(e)}), 200
    return jsonify({"ok": True}), 200

@app.route("/webhook/<path_token>", methods=["POST"])
def webhook_tokened(path_token):
    if APP_TOKEN_IN_PATH and not MISSING_TOKEN and path_token != TOKEN:
        return "forbidden", 403
    return _process_update_common()

@app.route("/webhook", methods=["POST"])
def webhook():
    if APP_TOKEN_IN_PATH:
        return "forbidden", 403
    return _process_update_common()

@app.route("/send_test", methods=["GET"])
def send_test():
    if MISSING_TOKEN:
        return "TELEGRAM_BOT_TOKEN not set", 503
    chat_id = request.args.get("chat_id")
    text = request.args.get("text", "Test message from TrustMe AI bot")
    if not chat_id:
        return "chat_id required", 400
    try:
        bot.send_message(chat_id=chat_id, text=text)
        return f"Sent to {chat_id}", 200
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
