import asyncpg
import logging
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Устанавливает подключение к базе данных."""
        try:
            self.pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                min_size=1,
                max_size=5
            )
            logging.info(f"Успешное подключение к PostgreSQL на {DB_HOST}:{DB_PORT}, БД: {DB_NAME}")
        except Exception as e:
            logging.error(f"Ошибка подключения к PostgreSQL: {e}")
            logging.error(f"Параметры подключения -> Хост: {DB_HOST}, Порт: {DB_PORT}, БД: {DB_NAME}, Пользователь: {DB_USER}")

    async def close(self):
        """Закрывает пул подключений."""
        if self.pool:
            await self.pool.close()
            logging.info("Подключение к PostgreSQL закрыто")

    async def save_message(self, user_id: int, message: str, gpt_response: str):
        """Сохраняет сообщение пользователя и ответ GPT в базу данных."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return

        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO chat_history (user_id, message, gpt_response, timestamp)
                    VALUES ($1, $2, $3, NOW())
                    """,
                    user_id, message, gpt_response
                )
                logging.info(f"Сообщение от пользователя {user_id} сохранено.")
        except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.exceptions.ConnectionFailureError) as e:
            logging.error(f"Потеряно соединение с базой данных: {e}")
            logging.info("Попытка переподключения...")
            await self.connect()
            await self.save_message(user_id, message, gpt_response)
        except Exception as e:
            logging.error(f"Ошибка при сохранении сообщения: {e}")

    async def get_recent_messages(self, user_id: int, limit: int = 10):
        """Получает последние сообщения пользователя из базы данных."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return []

        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT message, gpt_response, timestamp 
                    FROM chat_history 
                    WHERE user_id = $1 
                    ORDER BY timestamp DESC 
                    LIMIT $2
                    """,
                    user_id, limit
                )
                return rows
        except Exception as e:
            logging.error(f"Ошибка при получении сообщений: {e}")
            return []
