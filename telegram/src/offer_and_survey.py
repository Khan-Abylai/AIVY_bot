import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler


OFFER_MESSAGE = (
    "Добро пожаловать в Aivy Life!\n"
    "Мы уважаем вашу конфиденциальность, и ваши данные остаются только в рамках проекта.\n"
    "Ваши сообщения используются исключительно для персонализации рекомендаций и не передаются третьим лицам.\n"
    "Подробнее о конфиденциальности – [ссылка на политику](https://example.com/privacy.pdf).\n"
    "Используя AI-чат, вы соглашаетесь с нашей политикой.\n\n"
    "Напишите \"Согласен\" или нажмите на кнопку, чтобы продолжить."
)

# Клавиатура с кнопкой "Начать"
START_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("/start")]],
    resize_keyboard=True,
    one_time_keyboard=True   # Если нужно, чтобы кнопка появлялась один раз
)

AGREE_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("Согласен")]],
    resize_keyboard=True,
    one_time_keyboard=True   # Если нужно, чтобы кнопка появлялась один раз
)

# Состояния анкеты
WAITING_FOR_CONSENT, FIRST_NAME, LAST_NAME, AGE, SEX, JOB, CITY, GOAL, SOLUTION = range(9)

async def start_offer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    user_id = update.effective_user.id
    user_exists = await db.check_user_exists(user_id)
    survey_completed = context.user_data.get('survey_completed', False)

    if not user_exists:
        await db.register_user(user_id)
        await update.message.reply_text(
            OFFER_MESSAGE,
            reply_markup=AGREE_KEYBOARD,
            parse_mode='Markdown'  # Для корректного отображения ссылки
        )
        return WAITING_FOR_CONSENT
    elif not survey_completed:
        await update.message.reply_text("Введите ваше имя:")
        return FIRST_NAME
    else:
        await update.message.reply_text("Привет снова! Я AIVY. Чем могу помочь?")
        return ConversationHandler.END

async def check_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "согласен" or "согласна":
        await update.message.reply_text("Введите ваше имя:")
        return FIRST_NAME
    else:
        await update.message.reply_text("Пожалуйста, напишите 'Согласен', чтобы продолжить, или нажмите на кнопку.", reply_markup=AGREE_KEYBOARD)
        return WAITING_FOR_CONSENT

async def process_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    first_name = update.message.text.strip()
    if not first_name:
        await update.message.reply_text("Имя не может быть пустым. Введите ваше имя:")
        return FIRST_NAME
    context.user_data['f_name'] = first_name
    await update.message.reply_text("Введите вашу фамилию:")
    return LAST_NAME

async def process_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    last_name = update.message.text.strip()
    if not last_name:
        await update.message.reply_text("Фамилия не может быть пустой. Введите вашу фамилию:")
        return LAST_NAME
    context.user_data['l_name'] = last_name
    await update.message.reply_text("Сколько вам лет?")
    return AGE

async def process_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    age_text = update.message.text
    numbers = re.findall(r'\d+', age_text)
    if not numbers:
        await update.message.reply_text("Пожалуйста, введите свой возраст числом (например, 25).")
        return AGE
    context.user_data['age'] = numbers[0]
    await update.message.reply_text("Ваш пол (м/ж/предпочитаю не указывать)?")
    return SEX

async def process_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['sex'] = update.message.text.strip()
    await update.message.reply_text("В какой сфере вы работаете или учитесь?")
    return JOB

async def process_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['job'] = update.message.text.strip()
    await update.message.reply_text("В каком городе/стране вы проживаете?")
    return CITY

async def process_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text.strip()
    await update.message.reply_text("Что побудило вас обратиться к AIvy? (Тревога, стресс, выгорание, одиночество, поиск себя, другое)")
    return GOAL

async def process_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['goal'] = update.message.text.strip()
    await update.message.reply_text("Какие задачи вы хотите решить с помощью AIvy? (Снять стресс, лучше понимать свои эмоции, найти мотивацию, другое)")
    return SOLUTION

async def process_solution(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    user_id = update.effective_user.id
    context.user_data['solution'] = update.message.text.strip()

    # Сохраняем профиль пользователя (обязательные поля: f_name и l_name)
    await db.save_user_profile(
        user_id,
        context.user_data['f_name'],
        context.user_data['l_name'],
        context.user_data['age'],
        context.user_data['sex'],
        context.user_data.get('job', ''),
        context.user_data.get('city', ''),
        context.user_data['goal'],
        context.user_data['solution']
    )

    context.user_data['survey_completed'] = True
    await update.message.reply_text("Спасибо за ответы! Теперь вы можете начать общение с AIvy. Напишите что угодно!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Функция отмены анкеты."""
    await update.message.reply_text("Процесс прерван. Напишите /start, или нажмите на кнопку, чтобы начать заново.", reply_markup=START_KEYBOARD)
    return ConversationHandler.END
