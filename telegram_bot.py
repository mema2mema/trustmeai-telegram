import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

def send_message(chat_id, text):
    url = BASE_URL + "sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    requests.post(url, data=data)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "✅ RedTrustBot is now active via webhook!")
        elif text == "/ping":
            send_message(chat_id, "🏓 Pong from Railway!")
        else:
            send_message(chat_id, f"🤖 You said: {text}")

    return {"ok": True}

@app.route("/")
def home():
    return "✅ RedTrustBot is live!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
