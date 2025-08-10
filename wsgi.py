
import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher
from telegram.utils.request import Request

# Import your handlers and registration from the package
from telegram_bot import register_handlers

# Environment
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN env var not set")

APP_TOKEN_IN_PATH = os.environ.get('APP_TOKEN_IN_PATH', '1') == '1'  # protect /webhook/<token> route

# Bot & dispatcher (PTB v13 style)
request = Request(con_pool_size=8)
bot = Bot(token=TOKEN, request=request)
dispatcher = Dispatcher(bot, None, workers=2, use_context=True)
register_handlers(dispatcher)
print("[wsgi] Dispatcher ready with workers=2")

# Flask app
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "<h1>TrustMe AI Telegram Bot is running ✅</h1><p>Use /health for status.</p>", 200



@app.route("/send_test", methods=["GET"])
def send_test():
    chat_id = request.args.get("chat_id")
    text = request.args.get("text", "Test message from TrustMe AI bot")
    if not chat_id:
        return "chat_id required", 400
    try:
        bot.send_message(chat_id=chat_id, text=text)
        return f"Sent to {chat_id}", 200
    except Exception as e:
        return str(e), 500


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

@app.route("/webhook/<path_token>", methods=["POST"])
def webhook_tokened(path_token):
    if APP_TOKEN_IN_PATH and path_token != TOKEN:
        return "forbidden", 403
    return _process_update()

@app.route("/webhook", methods=["POST"])
def webhook():
    # Fallback if you ever set webhook without token path
    if APP_TOKEN_IN_PATH:
        return "forbidden", 403
    return _process_update()

def _process_update():
    try:
        payload = request.get_json(force=True)
    print('[webhook] Incoming update:', payload)
    update = Update.de_json(payload, bot)
        dispatcher.process_update(update)
    except Exception as e:
        # Always respond 200 to keep webhook active; include error info
        return jsonify({"ok": False, "error": str(e)}), 200
    return jsonify({"ok": True}), 200

if __name__ == "__main__":
    # Local run (Telegram can't reach without ngrok)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
