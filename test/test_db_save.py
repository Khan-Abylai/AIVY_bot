import sys
import os
# Добавляем путь к каталогу, где находится database.py (в вашем случае: telegram/src)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'telegram', 'src'))

import asyncio
import logging
from database import Database

logging.basicConfig(level=logging.INFO)

async def test_save_messages():
    db = Database()
    await db.connect()

    # Очистка таблицы Conversation для тестового окружения
    async with db.pool.acquire() as connection:
        await connection.execute('TRUNCATE TABLE "Conversation" RESTART IDENTITY CASCADE;')
        logging.info("Таблица Conversation очищена и последовательность сброшена.")

    # Используем тестового пользователя с уникальным ID (например, 9999)
    test_user_id = 9999

    # Регистрируем тестового пользователя, чтобы его ID существовал в таблице "USER"
    await db.register_user(test_user_id)

    # Создаем новый диалог
    dialogue_id = await db.create_conversation()
    if dialogue_id == 0:
        logging.error("Не удалось создать диалог для теста.")
        await db.close()
        return

    # Определяем тестовые сообщения
    user_message = "Привет, бот! Это тестовое сообщение."
    assistant_response = "Здравствуйте! Это ответ тестового бота."

    # Сохраняем сообщения с привязкой к диалогу
    await db.save_message_with_dialogue(test_user_id, dialogue_id, 'user', user_message)
    await db.save_message_with_dialogue(test_user_id, dialogue_id, 'assistant', assistant_response)

    # Извлекаем последние сообщения для данного пользователя
    messages = await db.get_recent_messages(test_user_id, limit=10)
    logging.info(f"Полученные сообщения: {messages}")

    # Проверяем, что тестовые сообщения присутствуют
    user_found = any(msg.get('message') == user_message for msg in messages)
    assistant_found = any(msg.get('gpt_response') == assistant_response for msg in messages)

    if user_found and assistant_found:
        print("Тест пройден: сообщения успешно сохранены в базе данных.")
    else:
        print("Тест НЕ пройден: сообщения не найдены в базе данных.")

    await db.close()

if __name__ == '__main__':
    asyncio.run(test_save_messages())
