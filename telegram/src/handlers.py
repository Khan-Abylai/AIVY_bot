import logging
from telegram import Update
from telegram.ext import ContextTypes
import requests
import config  # Убедитесь, что модуль config импортирован

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Отправь сообщение, давай поговорим.\n"
        "/feedback - оставить обратную связь\n"
        "/history - посмотреть историю сообщений\n"
        "/myprofile - посмотреть свой профиль"
    )
    await update.message.reply_text(help_text)

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    user_id = update.message.from_user.id
    messages = await db.get_recent_messages(user_id)
    if not messages:
        await update.message.reply_text("История пуста.")
        return
    history_text = "📜 Последние сообщения:\n\n"
    for msg in messages:
        history_text += f"👤 {msg['message']}\n🤖 {msg['gpt_response']}\n🕒 {msg['timestamp']}\n\n"
    await update.message.reply_text(history_text)

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    user_id = update.message.from_user.id
    survey_completed = context.user_data.get('survey_completed', False)
    if survey_completed:
        user_text = update.message.text
        try:
            # Отправка запроса к GPT API
            response = requests.post(config.GPT_API_URL, data={"prompt": user_text})
            response.raise_for_status()
            gpt_answer = response.json().get("response", "Ошибка: пустой ответ от API")
            await update.message.reply_text(gpt_answer)
            # Сохранение сообщения (старый метод или новый метод можно использовать)
            await db.save_message(user_id, user_text, gpt_answer)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуй снова позже.")
    else:
        await update.message.reply_text("Пожалуйста, закончите анкетирование. Напишите /start, если что-то пошло не так.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, я не знаю такой команды. Используйте /help для списка команд.")

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    user_id = update.message.from_user.id
    profile = await db.get_user_profile(user_id)
    if profile:
        text = (
            f"Ваш профиль:\n"
            f"Имя: {profile['f_name']}\n"
            f"Фамилия: {profile['l_name']}\n"
            f"Возраст: {profile['age']}\n"
            f"Пол: {profile['sex']}\n"
            f"Профессия: {profile['job']}\n"
            f"Город: {profile['city']}\n"
            f"Цель: {profile['goal']}\n"
            f"Решение: {profile.get('solution', '')}"
        )
    else:
        text = "Профиль не найден. Завершите анкетирование командой /start."
    await update.message.reply_text(text)
