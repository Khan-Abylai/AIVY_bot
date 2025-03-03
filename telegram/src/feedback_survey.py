from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# Состояния для финального опроса
(RATING, USEFUL, MISSING, INTERFACE, IMPROVEMENTS) = range(5)


async def start_feedback_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Мы ежедневно работаем над улучшением AIvy и будем рады вашей обратной связи!\n\nКак вы оцениваете своё взаимодействие с AIvy? (Очень полезно, полезно, нейтрально, мало пользы, бесполезно)")
    return RATING


async def process_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['rating'] = update.message.text
    await update.message.reply_text(
        "Какие функции AIvy вам наиболее полезны? (Анализ эмоций, поддерживающие фразы, медитации, рефлексивные вопросы, другое)")
    return USEFUL


async def process_useful(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['useful'] = update.message.text
    await update.message.reply_text("Чего, по вашему мнению, не хватает в AIvy, чтобы она лучше помогала вам?")
    return MISSING


async def process_missing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['missing'] = update.message.text
    await update.message.reply_text(
        "Насколько удобен интерфейс и функционал AIvy? (Очень удобен, удобен, нейтрально, неудобен, очень неудобен)")
    return INTERFACE


async def process_interface(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['interface'] = update.message.text
    await update.message.reply_text("Что бы вам хотелось улучшить в AIvy с технической точки зрения?")
    return IMPROVEMENTS


async def process_improvements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    context.user_data['improvements'] = update.message.text

    await db.save_user_feedback(
        user_id,
        context.user_data['rating'],
        context.user_data['useful'],
        context.user_data['missing'],
        context.user_data['interface'],
        context.user_data['improvements']
    )

    await update.message.reply_text("Спасибо за обратную связь! Мы ценим ваше мнение.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Процесс прерван. Напишите /feedback, чтобы начать заново.")
    return ConversationHandler.END