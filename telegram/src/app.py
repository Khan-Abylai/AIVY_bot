import logging
import nest_asyncio
import asyncio
import aiohttp
import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
from zoneinfo import ZoneInfo
import config
from offer_and_survey import (
    start_offer, check_consent, process_first_name, # process_last_name,
    process_age, process_sex, process_marital_status, process_job, process_city, process_goal, process_solution, cancel,
    WAITING_FOR_CONSENT, FIRST_NAME, LAST_NAME, AGE, SEX, MARITAL_STATUS, JOB, CITY, GOAL, SOLUTION
)
from feedback_survey import (
    start_feedback_survey, process_rating, process_useful, process_missing,
    process_interface, process_improvements, cancel as feedback_cancel,
    RATING, USEFUL, MISSING, INTERFACE, IMPROVEMENTS
)
from handlers import process_message, help_command, show_history, unknown_command, my_profile  # Обновлён импорт
from summary_utils import process_summary_for_all_users

nest_asyncio.apply()
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

db = Database()

async def call_gpt_api(prompt: str) -> str:
    url = config.GPT_API_URL  # e.g. "http://api_gpt:9001/api/generate"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"prompt": prompt}) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("response", "Нет ответа")
        except Exception as e:
            logging.error(f"Error calling GPT API: {e}")
            return "Извините, произошла ошибка. Попробуйте снова позже."

async def reset_chat(update, context):
    user_id = update.message.chat_id
    await update.message.reply_text("История диалога очищена.")

async def schedule_summaries():
    """
    Фоновая задача, которая каждые n минуты генерирует summary для всех пользователей за заданную дату.
    :param db: Экземпляр класса Database для доступа к базе данных.
    """
    await asyncio.sleep(config.summary_start_sleep_time)  # небольшая задержка для старта
    tz = ZoneInfo("Asia/Almaty")
    while True:
        # now = datetime.datetime.now(tz)
        # next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        # if now >= next_run:
        #     next_run += datetime.timedelta(days=1)
        # sleep_seconds = (next_run - now).total_seconds()
        # await asyncio.sleep(sleep_seconds)
        try:
            date_to_summarize = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")  # прошлый день
            #date_to_summarize = datetime.datetime.now().strftime("%Y-%m-%d")  # этот день
            await process_summary_for_all_users(db, date_to_summarize)
        except Exception as e:
            logging.error(f"[schedule_summaries] Ошибка: {e}")
        await asyncio.sleep(config.summary_update_loop_time)  # повторяем каждые n минуты

async def main():
    logging.info("Starting Telegram bot...")
    await db.connect()
    app = Application.builder().token(config.TOKEN).build()

    offer_handler = ConversationHandler(
        entry_points=[CommandHandler("start", lambda update, context: start_offer(update, context, db))],
        states={
            WAITING_FOR_CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_consent)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_first_name)],
            # LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_age)],
            SEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_sex)],
            MARITAL_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_marital_status)],
            JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_job)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_city)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_goal)],
            SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: process_solution(update, context, db))]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    feedback_survey_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", start_feedback_survey)],
        states={
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_rating)],
            USEFUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_useful)],
            MISSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_missing)],
            INTERFACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_interface)],
            IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: process_improvements(update, context, db))]
        },
        fallbacks=[CommandHandler("cancel", feedback_cancel)]
    )

    # Добавляем обработчики с передачей db
    app.add_handler(offer_handler)
    app.add_handler(feedback_survey_handler)
    app.add_handler(CommandHandler("help", lambda update, context: help_command(update, context, db)))
    app.add_handler(CommandHandler("history", lambda update, context: show_history(update, context, db)))
    app.add_handler(CommandHandler("myprofile", lambda update, context: my_profile(update, context, db)))
    app.add_handler(CommandHandler("reset", reset_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: process_message(update, context, db)))
    app.add_handler(MessageHandler(filters.COMMAND, lambda update, context: unknown_command(update, context, db)))

    asyncio.create_task(schedule_summaries())  # Запускаем фоновую задачу

    logging.info("Telegram bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())