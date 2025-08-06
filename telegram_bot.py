from flask import Flask, request
import telegram
import os

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telegram.Bot(token=TOKEN)

app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text

    if text == '/start':
        bot.send_message(chat_id=chat_id, text="✅ RedTrustBot is now active via webhook!")
    else:
        bot.send_message(chat_id=chat_id, text=f"🧠 You said: {text}")
    return 'ok'

@app.route('/', methods=['GET'])
def home():
    return '✅ TrustMe AI Bot is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
