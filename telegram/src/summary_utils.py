import logging
from database import Database
import config
import aiohttp

async def build_dialog_text_for_dialogue(db: Database, dialogue_id: int, date: str) -> str:
    """
    Формирует текст диалога для суммаризации для заданного dialogue_id за указанную дату.
    Собирает все сообщения из диалога и добавляет начальный prompt.
    """
    messages = await db.get_messages_for_dialogue_for_date(dialogue_id, date)
    if not messages:
        return ""
    lines = []
    for msg in messages:
        if msg["role"].lower() == "user":
            lines.append(f"User: {msg['response']}")
        else:
            lines.append(f"Assistant: {msg['response']}")
    return "\n".join(lines)

async def call_summary_api(dialog_text: str) -> str:
    """
    Вызывает внешний API для суммаризации текста диалога.

    Функция отправляет HTTP POST-запрос к эндпоинту суммаризации (адрес задаётся в конфигурации)
    с сформированным текстом диалога и возвращает сгенерированный summary.

    :param dialog_text: Текст диалога, сформированный для суммаризации.
    :return: Сгенерированный summary в виде строки. Если произошла ошибка, возвращается пустая строка.
    """
    url = config.SUMMARY_API_URL  # e.g. "http://gpt_api:9001/api/summarize"
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"dialog_text": dialog_text}
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("summary", "")
        except Exception as e:
            logging.error(f"Ошибка при вызове /api/summarize: {e}")
            return ""

async def process_summary_for_all_users(db: Database, date: str):
    """
    Обходит все dialogue_id, имеющие сообщения за указанную дату,
    генерирует summary для каждого и сохраняет его.
    """
    dialogue_ids = await db.get_all_dialogue_ids_for_date(date)
    for dialogue_id in dialogue_ids:
        dialog_text = await build_dialog_text_for_dialogue(db, dialogue_id, date)
        if not dialog_text.strip():
            continue
        summary = await call_summary_api(dialog_text)
        if summary:
            did = await db.upsert_conversation_summary(dialogue_id, summary)
            logging.info(f"[summary_worker] Summary сохранён для диалога {did}")
