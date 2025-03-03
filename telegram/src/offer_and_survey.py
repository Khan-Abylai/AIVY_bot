from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

OFFER_MESSAGE = """
Добро пожаловать в Aivy Life!  
Мы уважаем вашу конфиденциальность, и ваши данные остаются только в рамках проекта.  
Ваши сообщения используются исключительно для персонализации рекомендаций и не передаются третьим лицам.  
Подробнее о конфиденциальности – [ссылка на политику](https://example.com/privacy.pdf).  
Используя AI-чат, вы соглашаетесь с нашей политикой.  

Напишите "Согласен", чтобы продолжить.
"""

WAITING_FOR_CONSENT, AGE, SEX, JOB, CITY, REASON, GOAL = range(7)

async def start_offer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    user_id = update.message.from_user.id
    user_exists = await db.check_user_exists(user_id)
    survey_completed = context.user_data.get('survey_completed', False)

    if not user_exists:
        await db.register_user(user_id)
        await update.message.reply_text(OFFER_MESSAGE)
        return WAITING_FOR_CONSENT
    elif not survey_completed:
        await update.message.reply_text("Сколько вам лет?")
        return AGE
    else:
        await update.message.reply_text("Привет снова! Я AIVY. Чем могу помочь?")
        return ConversationHandler.END


async def check_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "согласен":
        await update.message.reply_text("Сколько вам лет?")
        return AGE
    else:
        await update.message.reply_text("Пожалуйста, напишите 'Согласен', чтобы продолжить.")
        return WAITING_FOR_CONSENT


async def process_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['age'] = update.message.text
    await update.message.reply_text("Ваш пол (м/ж/предпочитаю не указывать)?")
    return SEX


async def process_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['sex'] = update.message.text
    await update.message.reply_text("В какой сфере вы работаете или учитесь?")
    return JOB


async def process_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['job'] = update.message.text
    await update.message.reply_text("В каком городе/стране вы проживаете?")
    return CITY


async def process_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text
    await update.message.reply_text("Что побудило вас обратиться к AIvy? (Тревога, стресс, выгорание, одиночество, поиск себя, другое)")
    return REASON


async def process_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['reason'] = update.message.text
    await update.message.reply_text("Какие задачи вы хотите решить с помощью AIvy? (Снять стресс, лучше понимать свои эмоции, найти мотивацию, другое)")
    return GOAL


async def process_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    context.user_data['goal'] = update.message.text

    # Сохраняем профиль в базу данных
    await db.save_user_profile(
        user_id,
        context.user_data['age'],
        context.user_data['sex'],
        context.user_data['job'],
        context.user_data['city'],
        context.user_data['reason'],
        context.user_data['goal']
    )

    context.user_data['survey_completed'] = True
    await update.message.reply_text("Спасибо за ответы! Теперь вы можете начать общение с AIvy. Напишите что угодно!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Процесс прерван. Напишите /start, чтобы начать заново.")
    return ConversationHandler.END