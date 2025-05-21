import logging
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext
)
import config

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: CallbackContext):
    """Приветственное сообщение при старте бота"""
    await update.message.reply_text(
        "Привет! Aivy, эмоциональный AI-компаньон.\n"
        "Просто отправьте мне сообщение, и я отвечу на него!"
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "*Как пользоваться:*\n"
        "- Отправьте любое сообщение, и я обработаю его через GPT API.\n"
        "- Доступные команды:\n"
        "   • /help — показать это сообщение\n"
        "   • /clear — очистить историю текущей сессии (за сегодня)\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def clear_session(update: Update, context: CallbackContext):
    """Очищает историю текущей сессии пользователя (за сегодня)."""
    user_id = update.effective_user.id
    today = datetime.utcnow().date().isoformat()
    session_id = f"{user_id}-{today}"
    try:
        resp = requests.post(config.CLEAR_API_URL, json={"session_id": session_id})
        resp.raise_for_status()
        await update.message.reply_text("История текущей сессии очищена.")
    except requests.RequestException as e:
        logging.error(f"Ошибка очистки сессии {session_id}: {e}")
        await update.message.reply_text("Не удалось очистить историю сессии. Попробуйте позже.")


async def process_message(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения и отправляет их в GPT API"""
    user_text = update.message.text
    user_id = update.effective_user.id
    # session_id, обновляемое раз в сутки
    today = datetime.utcnow().date().isoformat()
    session_id = f"{user_id}-{today}"

    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "user_input": user_text
    }

    try:
        # Отправляем JSON-пэйлоуд в GPT API
        response = requests.post(config.GPT_API_URL, json=payload)
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
    app.add_handler(CommandHandler("clear", clear_session))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
