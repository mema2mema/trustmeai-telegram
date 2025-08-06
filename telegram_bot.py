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
    bot.sendMessage(chat_id=chat_id, text="✅ RedTrustBot is now active via webhook!")
    return 'ok'

@app.route('/')
def index():
    return '✅ TrustMe AI Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
