
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from utils import generate_summary, generate_graph, analyze_backtest
from insight_engine import generate_insight

with open('telegram_config.json') as f:
    config = json.load(f)

TOKEN = config['bot_token']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 TrustMe AI Bot is online. Use /summary /log /graph /upload /insight')

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = generate_summary()
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_document(open('trades.csv', 'rb'))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        generate_graph()
        await update.message.reply_photo(photo=open('graph.png', 'rb'))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = await update.message.document.get_file()
        file_path = f"uploaded_backtest.csv"
        await file.download_to_drive(file_path)
        summary = analyze_backtest(file_path)
        await update.message.reply_text(summary)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ai_result = generate_insight("trades.csv")
        await update.message.reply_text(ai_result)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("insight", insight))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ATTACHMENT, upload_file))
    app.run_polling()

if __name__ == '__main__':
    main()
