
import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher
from telegram.utils.request import Request
from telegram_bot import register_handlers

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
APP_TOKEN_IN_PATH = os.environ.get("APP_TOKEN_IN_PATH", "0") == "1"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    if not TOKEN:
        return "<h1>TrustMe AI Bot ⚠️</h1><p>Set TELEGRAM_BOT_TOKEN in Railway Variables.</p>", 200
    return "<h1>TrustMe AI Telegram Bot is running ✅</h1><p>Use /health for status.</p>", 200

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

bot = None
dispatcher = None
if TOKEN:
    req = Request(con_pool_size=8)
    bot = Bot(token=TOKEN, request=req)
    dispatcher = Dispatcher(bot, None, workers=2, use_context=True)
    register_handlers(dispatcher)
    print("[wsgi] Dispatcher ready with workers=2")
else:
    print("[wsgi] WARNING: TELEGRAM_BOT_TOKEN missing. Bot not initialized.")

def _process_update():
    if not TOKEN:
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
    if APP_TOKEN_IN_PATH:
        if not TOKEN or path_token != TOKEN:
            return "forbidden", 403
        return _process_update()
    return _process_update()

@app.route("/webhook", methods=["POST"])
def webhook():
    if APP_TOKEN_IN_PATH:
        return "forbidden", 403
    return _process_update()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
