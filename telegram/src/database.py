import asyncpg
import logging
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
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
        if self.pool:
            await self.pool.close()
            logging.info("Подключение к PostgreSQL закрыто")

    async def check_user_exists(self, user_id: int) -> bool:
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return False
        try:
            async with self.pool.acquire() as connection:
                result = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM \"USER\" WHERE user_id = $1)", user_id
                )
                return result
        except Exception as e:
            logging.error(f"Ошибка при проверке пользователя: {e}")
            return False

    async def register_user(self, user_id: int):
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    "INSERT INTO \"USER\" (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", user_id
                )
                logging.info(f"Пользователь {user_id} зарегистрирован.")
        except Exception as e:
            logging.error(f"Ошибка при регистрации пользователя: {e}")

    async def save_message(self, user_id: int, message: str, gpt_response: str):
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "Message" (user_id, dialogue_id, role, response)
                    VALUES ($1, (SELECT COALESCE(MAX(dialogue_id), 1) FROM "Conversation"), 'user', $2)
                    """,
                    user_id, message
                )
                await connection.execute(
                    """
                    INSERT INTO "Message" (user_id, dialogue_id, role, response)
                    VALUES ($1, (SELECT COALESCE(MAX(dialogue_id), 1) FROM "Conversation"), 'assistant', $3)
                    """,
                    user_id, gpt_response
                )
                logging.info(f"Сообщение от пользователя {user_id} сохранено.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении сообщения: {e}")

    async def get_recent_messages(self, user_id: int, limit: int = 10):
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return []
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT response, role, response_time 
                    FROM "Message" 
                    WHERE user_id = $1 
                    ORDER BY response_time DESC 
                    LIMIT $2
                    """,
                    user_id, limit
                )
                return [{'message': row['response'] if row['role'] == 'user' else None,
                        'gpt_response': row['response'] if row['role'] == 'assistant' else None,
                        'timestamp': row['response_time']} for row in rows]
        except Exception as e:
            logging.error(f"Ошибка при получении сообщений: {e}")
            return []

    async def save_user_profile(self, user_id: int, age: str, sex: str, job: str, city: str, reason: str, goal: str):
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "USER_Profile" (user_id, age, sex, job, city, goal)
                    VALUES ($1, $2::int, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE SET age = $2::int, sex = $3, job = $4, city = $5, goal = $6
                    """,
                    user_id, int(age), sex, job, city, goal
                )
            logging.info(f"Профиль пользователя {user_id} сохранён.")
        except ValueError as ve:
            logging.error(f"Некорректный возраст для пользователя {user_id}: {ve}")
        except Exception as e:
            logging.error(f"Ошибка при сохранении профиля пользователя: {e}")

    async def save_user_feedback(self, user_id: int, rating: str, useful: str, missing: str, interface: str, improvements: str):
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "USER_Feedback" (user_id, interaction_rating, useful_functions, missing_features, interface_convenience, technical_improvements)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE SET interaction_rating = $2, useful_functions = $3, missing_features = $4, interface_convenience = $5, technical_improvements = $6
                    """,
                    user_id, rating, useful, missing, interface, improvements
                )
            logging.info(f"Обратная связь пользователя {user_id} сохранена.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении обратной связи: {e}")