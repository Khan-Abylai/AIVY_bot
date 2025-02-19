import logging
import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import requests
from database import Database
import config

nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я AIVY. Отправь мне сообщение!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "Отправь сообщение, давай поговорим."
    await update.message.reply_text(help_text)

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    messages = await db.get_recent_messages(user_id)

    if not messages:
        await update.message.reply_text("История пуста.")
        return

    history_text = "📜 Последние сообщения:\n\n"
    for msg in messages:
        history_text += f"👤 {msg['message']}\n🤖 {msg['gpt_response']}\n🕒 {msg['timestamp']}\n\n"

    await update.message.reply_text(history_text)

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id

    try:
        response = requests.post(config.GPT_API_URL, data={"prompt": user_text})
        response.raise_for_status()

        gpt_answer = response.json().get("response", "Ошибка: пустой ответ от API")
        await update.message.reply_text(gpt_answer)

        # Сохраняем в базу данных
        await db.save_message(user_id, user_text, gpt_answer)

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй снова позже.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, я не знаю такой команды.")

async def main():

    await db.connect()

    app = Application.builder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
