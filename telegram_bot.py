
import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = "YOUR_REAL_BOT_TOKEN_HERE"
WEBHOOK_URL = "https://your-railway-url.ngrok-free.app/webhook"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("🔍 Incoming Telegram data:", data)  # Debug print

    if not data or "message" not in data:
        return "ignored", 200

    chat_id = data["message"]["chat"]["id"]
    message = data["message"].get("text", "")

    send_message(chat_id, f"✅ Your CHAT_ID is: {chat_id}")
    return "ok", 200

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    set_hook = requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}")
    return set_hook.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
