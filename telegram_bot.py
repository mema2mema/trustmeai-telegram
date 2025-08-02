import json
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from utils import generate_summary, generate_graph

with open("telegram_config.json") as f:
    config = json.load(f)

TOKEN = config["bot_token"]
CHAT_ID = config["chat_id"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 TrustMe AI bot is online!")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = generate_summary()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buf = generate_graph()
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("graph", graph))
    app.run_polling()
