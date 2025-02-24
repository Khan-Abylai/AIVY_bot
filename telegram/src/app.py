import logging
import nest_asyncio
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
import config
from offer_and_survey import start_offer, check_consent, process_age, process_sex, process_job, process_city, process_reason, process_goal, cancel, WAITING_FOR_CONSENT, AGE, SEX, JOB, CITY, REASON, GOAL
from feedback_survey import start_feedback_survey, process_rating, process_useful, process_missing, process_interface, process_improvements, cancel as feedback_cancel, RATING, USEFUL, MISSING, INTERFACE, IMPROVEMENTS
from handlers import help_command, show_history, process_message, unknown_command

nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

db = Database()

async def main():
    await db.connect()

    app = Application.builder().token(config.TOKEN).build()

    # Обработчик оферты и анкетирования
    offer_handler = ConversationHandler(
        entry_points=[CommandHandler("start", lambda update, context: start_offer(update, context, db))],
        states={
            WAITING_FOR_CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_consent)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_age)],
            SEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_sex)],
            JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_job)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_city)],
            REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reason)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_goal)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчик финального опроса
    feedback_survey_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", start_feedback_survey)],
        states={
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_rating)],
            USEFUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_useful)],
            MISSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_missing)],
            INTERFACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_interface)],
            IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_improvements)],
        },
        fallbacks=[CommandHandler("cancel", feedback_cancel)],
    )

    # Регистрация обработчиков
    app.add_handler(offer_handler)
    app.add_handler(feedback_survey_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", lambda update, context: show_history(update, context, db)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: process_message(update, context, db)))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())