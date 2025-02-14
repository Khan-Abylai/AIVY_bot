import os
import logging
import requests
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import config

# Словарь для хранения выбранного режима для каждого чата (chat_id: mode)
chat_modes = {}

def start(update, context):
    chat_id = update.effective_chat.id
    # По умолчанию устанавливаем режим "llama" (стандартный API)
    chat_modes[chat_id] = "llama"
    context.bot.send_message(
        chat_id=chat_id,
        text=("Привет! Я бот на базе Llama.\n\n"
              "По умолчанию я использую стандартный API (Llama).\n"
              "Чтобы переключиться на GPT API, отправьте команду /gpt.\n"
              "Чтобы переключиться обратно на Llama API, отправьте команду /llama.")
    )

def help_command(update, context):
    help_msg = (
        "*Как пользоваться:*\n"
        "- Отправьте любое сообщение — оно будет обработано выбранным API.\n"
        "- Для переключения режима:\n"
        "   • /gpt — использовать GPT API\n"
        "   • /llama — использовать стандартный API (Llama)\n"
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        parse_mode=telegram.ParseMode.MARKDOWN,
        text=help_msg
    )

def set_gpt_mode(update, context):
    chat_id = update.effective_chat.id
    chat_modes[chat_id] = "gpt"
    context.bot.send_message(
        chat_id=chat_id,
        text="Режим переключён: теперь используются запросы к GPT API."
    )

def set_llama_mode(update, context):
    chat_id = update.effective_chat.id
    chat_modes[chat_id] = "llama"
    context.bot.send_message(
        chat_id=chat_id,
        text="Режим переключён: теперь используются запросы к Llama API."
    )

def echo_text(update, context):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Определяем режим для данного чата, если не задан – по умолчанию "llama"
    mode = chat_modes.get(chat_id, "llama")
    
    # Выбираем URL в зависимости от выбранного режима
    if mode == "gpt":
        api_url = config.GPT_API_URL
    else:
        api_url = config.LLAMA_API_URL

    try:
        # Отправляем запрос к выбранному API
        resp = requests.post(api_url, data={"prompt": user_text})
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("response", "")
            context.bot.send_message(chat_id=chat_id, text=answer)
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text="Ошибка при запросе к API."
            )
    except Exception as e:
        logging.error(e)
        context.bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка при запросе к API."
        )

def unknown(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извините, я не знаю такой команды."
    )

def main():
    updater = Updater(config.TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Обработчики команд для старта и помощи
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    # Обработчики команд для переключения режима
    dispatcher.add_handler(CommandHandler("gpt", set_gpt_mode))
    dispatcher.add_handler(CommandHandler("llama", set_llama_mode))
    # Обработка неизвестных команд
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    # Обработка обычных текстовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
