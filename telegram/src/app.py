import logging
import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)
import config

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: CallbackContext):
    """Приветственное сообщение при старте бота"""
    await update.message.reply_text(
        "Привет! Я бот на базе GPT.\n"
        "Просто отправьте мне сообщение, и я отвечу на него!"
    )

async def help_command(update: Update, context: CallbackContext):
    """Выводит список команд"""
    help_text = (
        "*Как пользоваться:*\n"
        "- Отправьте любое сообщение, и я обработаю его через GPT API.\n"
        "- Доступные команды:\n"
        "   • /help — показать это сообщение\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def process_message(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения и отправляет их в GPT API"""
    user_text = update.message.text

    try:
        response = requests.post(config.GPT_API_URL, data={"prompt": user_text})
        response.raise_for_status()

        answer = response.json().get("response", "Ошибка: пустой ответ от API")
        await update.message.reply_text(answer)

    except requests.RequestException as e:
        logging.error(f"Ошибка запроса к GPT API: {e}")
        await update.message.reply_text("Произошла ошибка при запросе к GPT API.")

async def unknown_command(update: Update, context: CallbackContext):
    """Сообщает пользователю, если команда не распознана"""
    await update.message.reply_text("Извините, я не знаю такой команды.")

def main():
    """Основной процесс бота"""
    app = Application.builder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
