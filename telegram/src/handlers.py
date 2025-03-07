import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import requests
import config

# Клавиатура с кнопкой "Начать"
START_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("/start")]],
    resize_keyboard=True,
    one_time_keyboard=True   # Если нужно, чтобы кнопка появлялась один раз
)

async def check_survey_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> bool:
    """Проверяет, завершил ли пользователь анкетирование."""
    user_id = update.message.from_user.id
    profile = await db.get_user_profile(user_id)
    survey_completed = context.user_data.get('survey_completed', False) or bool(profile)
    context.user_data['survey_completed'] = survey_completed  # Обновляем статус в context
    return survey_completed

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):  # Добавляем db как аргумент
    if not await check_survey_completed(update, context, db):
        await update.message.reply_text(
            "Пожалуйста, закончите анкетирование. Напишите /start или нажмите на кнопку.",
            reply_markup=START_KEYBOARD
        )
        return
    help_text = (
        "Отправь сообщение, давай поговорим.\n"
        "/feedback - оставить обратную связь\n"
        "/history - посмотреть историю сообщений\n"
        "/myprofile - посмотреть свой профиль"
    )
    await update.message.reply_text(help_text)

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    if not await check_survey_completed(update, context, db):
        await update.message.reply_text(
            "Пожалуйста, закончите анкетирование. Напишите /start или нажмите на кнопку.",
            reply_markup=START_KEYBOARD
        )
        return
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
    if not await check_survey_completed(update, context, db):
        await update.message.reply_text(
            "Пожалуйста, закончите анкетирование. Напишите /start или нажмите на кнопку.",
            reply_markup=START_KEYBOARD
        )
        return
    user_id = update.message.from_user.id
    user_text = update.message.text
    try:
        # Получаем или создаём dialogue_id
        current_dialogue_id = context.user_data.get('current_dialogue_id')
        if not current_dialogue_id:  # Новый диалог, если ещё не создан
            current_dialogue_id = await db.create_conversation()
            context.user_data['current_dialogue_id'] = current_dialogue_id
            logging.info(f"Создан новый диалог {current_dialogue_id} для пользователя {user_id}")

        response = requests.post(config.GPT_API_URL, json={"prompt": user_text})  # Используем json вместо data
        response.raise_for_status()
        gpt_answer = response.json().get("response", "Ошибка: пустой ответ от API")
        await update.message.reply_text(gpt_answer)
        await db.save_message(user_id, user_text, gpt_answer, current_dialogue_id)  # Передаём current_dialogue_id
    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуй снова позже.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db):  # Добавляем db
    if not await check_survey_completed(update, context, db):
        await update.message.reply_text(
            "Пожалуйста, закончите анкетирование. Напишите /start или нажмите на кнопку.",
            reply_markup=START_KEYBOARD
        )
        return
    await update.message.reply_text("Извините, я не знаю такой команды. Используйте /help для списка команд.")

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    if not await check_survey_completed(update, context, db):
        await update.message.reply_text(
            "Пожалуйста, закончите анкетирование. Напишите /start или нажмите на кнопку.",
            reply_markup=START_KEYBOARD
        )
        return
    user_id = update.message.from_user.id
    profile = await db.get_user_profile(user_id)
    if profile:
        text = (
            f"Ваш профиль:\n"
            f"Имя: {profile['f_name']}\n"
            f"Фамилия: {profile['l_name']}\n"
            f"Возраст: {profile['age']}\n"
            f"Пол: {profile['sex']}\n"
            f"Семейное положение: {profile['marital_status']}\n"
            f"Профессия: {profile['job']}\n"
            f"Город: {profile['city']}\n"
            f"Цель: {profile['goal']}\n"
            f"Решение: {profile.get('solution', '')}"
        )
    else:
        text = "Профиль не найден. Завершите анкетирование командой /start или нажмите на кнопку."
    await update.message.reply_text(text, reply_markup=START_KEYBOARD)