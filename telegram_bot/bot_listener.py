from telegram.ext import ApplicationBuilder, CommandHandler
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("🚀 Hello from TrustMe AI Bot!")

def start_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_webhook(listen="0.0.0.0",
                    port=int(os.environ.get("PORT", 8080)),
                    url_path=TOKEN,
                    webhook_url=f"https://trustmeai-telegram-production.up.railway.app/{TOKEN}")