from flask import Flask, request
import os
import telegram

# --- Read token from environment (DO NOT hardcode) ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Configure it in Railway -> Variables.")

bot = telegram.Bot(token=TOKEN)
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text or ""

    if text.strip().lower() == "/start":
        bot.send_message(chat_id=chat_id, text="✅ RedTrustBot (webhook) is online!")
    elif text.strip().lower() == "/ping":
        bot.send_message(chat_id=chat_id, text="🏓 Pong (Railway).")
    else:
        bot.send_message(chat_id=chat_id, text=f"🤖 You said: {text}")
    return "ok"

@app.route("/", methods=["GET"])
def health():
    return "✅ TrustMe AI Telegram webhook is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
