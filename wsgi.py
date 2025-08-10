
import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher
from telegram.utils.request import Request
from telegram_bot import register_handlers, start_scheduler

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
APP_TOKEN_IN_PATH = os.environ.get("APP_TOKEN_IN_PATH", "0") == "1"

# Start scheduler at import (Gunicorn) — it's idempotent inside telegram_bot.start_scheduler
try:
    start_scheduler()
except Exception as _e:
    # Avoid hard crash if scheduler cannot start at import time
    print("Scheduler init warning:", _e)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    if not TELEGRAM_BOT_TOKEN:
        return "<h1>TrustMe AI Bot ⚠️</h1><p>Set TELEGRAM_BOT_TOKEN in Railway Variables.</p>", 200
    return "<h1>TrustMe AI Bot ✅</h1><p>Webhook endpoint is /webhook{opt}</p>".format(
        opt="/<TOKEN>" if APP_TOKEN_IN_PATH else ""
    ), 200

def _handle_webhook():
    body = request.get_json(force=True, silent=True)
    if not body:
        return "no json", 400
    req = Request(con_pool_size=8)
    bot = Bot(token=TELEGRAM_BOT_TOKEN, request=req)
    dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)
    register_handlers(dispatcher)
    update = Update.de_json(body, bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if APP_TOKEN_IN_PATH:
        return "forbidden", 403
    return _handle_webhook()

@app.route("/webhook/<path_token>", methods=["POST"])
def webhook_tokened(path_token):
    if APP_TOKEN_IN_PATH:
        if not TELEGRAM_BOT_TOKEN or path_token != TELEGRAM_BOT_TOKEN:
            return "forbidden", 403
    return _handle_webhook()
