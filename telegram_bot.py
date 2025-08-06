from flask import Flask, request
import telegram

TOKEN = '8418478395:AAGfJ8R2fvbsrwync2f5N3a33zgPH7066-A'
bot = telegram.Bot(token=TOKEN)
app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text
    bot.send_message(chat_id=chat_id, text="Received: " + text)
    return 'ok'

@app.route('/')
def index():
    return 'TrustMe AI Telegram Bot is running!'

if __name__ == '__main__':
    app.run(debug=True)