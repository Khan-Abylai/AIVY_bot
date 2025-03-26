import asyncpg
import asyncio
import logging
import datetime
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Устанавливает подключение к базе данных."""
        max_retries = 5
        retry_delay = 5  # секунды
        for attempt in range(max_retries):
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
                return
            except Exception as e:
                logging.error(f"Ошибка подключения к PostgreSQL: {e}")
                logging.error(f"Параметры подключения -> Хост: {DB_HOST}, Порт: {DB_PORT}, БД: {DB_NAME}, Пользователь: {DB_USER}")
                logging.error(f"Попытка {attempt + 1}/{max_retries} подключения к PostgreSQL не удалась: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)

    async def close(self):
        """Закрывает пул подключений."""
        if self.pool:
            await self.pool.close()
            logging.info("Подключение к PostgreSQL закрыто")

    async def check_user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь в таблице USER."""
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
        """Регистрирует нового пользователя в таблице USER."""
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

    async def save_message(self, user_id: int, message: str, gpt_response: str, dialogue_id: int):
        """Сохраняет сообщение пользователя и ответ GPT в базу данных с указанным dialogue_id."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "Message" (user_id, dialogue_id, role, response, emotion)
                    VALUES ($1, $2, 'user', $3::text, 'neutral')
                    """,
                    user_id, dialogue_id, message
                )
                await connection.execute(
                    """
                    INSERT INTO "Message" (user_id, dialogue_id, role, response, emotion)
                    VALUES ($1, $2, 'assistant', $3::text, 'positive')
                    """,
                    user_id, dialogue_id, gpt_response
                )
                logging.info(f"Сообщение от {user_id} сохранено в диалоге {dialogue_id}")
        except Exception as e:
            logging.error(f"Ошибка при сохранении сообщения: {e}", exc_info=True)

    async def get_recent_messages(self, user_id: int, limit: int = 10):
        """Получает последние сообщения пользователя из базы данных."""
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

    async def save_user_profile(self, user_id: int, f_name: str, l_name: str, age: str, sex: str, marital_status: str,
                                job: str, city: str, goal: str, solution: str):
        """Сохраняет или обновляет профиль пользователя, включая семейное положение."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "USER_Profile" (user_id, f_name, l_name, age, sex, marital_status, job, city, goal, solution)
                    VALUES ($1, $2, $3, $4::int, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (user_id) DO UPDATE SET 
                        f_name = $2,
                        l_name = $3,
                        age = $4::int,
                        sex = $5,
                        marital_status = $6,
                        job = $7,
                        city = $8,
                        goal = $9,
                        solution = $10
                    """,
                    user_id, f_name, l_name, int(age), sex, marital_status, job, city, goal, solution
                )
            logging.info(f"Профиль пользователя {user_id} сохранён.")
        except ValueError as ve:
            logging.error(f"Некорректный возраст для пользователя {user_id}: {ve}")
        except Exception as e:
            logging.error(f"Ошибка при сохранении профиля пользователя: {e}")

    async def save_user_feedback(self, user_id: int, rating: str, useful: str, missing: str, interface: str, improvements: str):
        """Сохраняет или обновляет обратную связь пользователя."""
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

    # Новые методы для работы с диалогами и сообщениями

    async def create_conversation(self) -> int:
        """Создаёт новый диалог в таблице Conversation и возвращает его dialogue_id."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return 0
        try:
            async with self.pool.acquire() as connection:
                dialogue_id = await connection.fetchval(
                    """
                    INSERT INTO "Conversation" (summary)
                    VALUES ('')
                    RETURNING dialogue_id
                    """
                )
                logging.info(f"Создан новый диалог: {dialogue_id}")
                return dialogue_id
        except Exception as e:
            logging.error(f"Ошибка при создании диалога: {e}")
            return 0

    async def save_message_with_dialogue(self, user_id: int, dialogue_id: int, role: str, message: str):
        """Сохраняет сообщение с привязкой к определённому диалогу (Conversation)."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO "Message" (user_id, dialogue_id, role, response)
                    VALUES ($1, $2, $3, $4::text)
                    """,
                    user_id, dialogue_id, role, message
                )
                logging.info(f"Сообщение ({role}) для пользователя {user_id} сохранено в диалоге {dialogue_id}.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении сообщения с диалогом: {e}")

    async def get_user_profile(self, user_id: int):
        """Получает профиль пользователя из таблицы USER_Profile."""
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return None
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    'SELECT * FROM "USER_Profile" WHERE user_id = $1', user_id
                )
                return row
        except Exception as e:
            logging.error(f"Ошибка при получении профиля пользователя: {e}")
            return None

    # Новые методы для работы с Conversation и summary

    async def get_all_dialogue_ids_for_date(self, date: str):
        """
        Возвращает список всех dialogue_id, в которых были сообщения за указанную дату.
        Преобразует входную строку в объект даты и использует DISTINCT для выборки.

        :param date: Дата в формате 'YYYY-MM-DD'.
        :return: Список dialogue_id (целых чисел) или пустой список, если нет сообщений.
        """
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except Exception as e:
            logging.error(f"Ошибка преобразования даты в get_all_dialogue_ids_for_date: {e}")
            return []
        query = """
            SELECT DISTINCT dialogue_id
            FROM "Message"
            WHERE date_trunc('day', response_time) = date_trunc('day', $1::date)
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, date_obj)
                dialogue_ids = [row["dialogue_id"] for row in rows]
                #logging.info(f"Найдено {len(dialogue_ids)} диалогов для даты {date_obj}")
                return dialogue_ids
        except Exception as e:
            logging.error(f"Ошибка get_all_dialogue_ids_for_date: {e}")
            return []

    async def get_messages_for_dialogue_for_date(self, dialogue_id: int, date: str):
        """
        Возвращает список сообщений для заданного dialogue_id за указанную дату.
        Преобразует входную строку в объект даты.

        :param dialogue_id: Идентификатор диалога.
        :param date: Дата в формате 'YYYY-MM-DD'.
        :return: Список словарей с полями 'role' и 'response'. Если сообщений нет, возвращается пустой список.
        """
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except Exception as e:
            logging.error(f"Ошибка преобразования даты в get_messages_for_dialogue_for_date: {e}")
            return []
        query = """
            SELECT role, response
            FROM "Message"
            WHERE dialogue_id = $1
              AND date_trunc('day', response_time) = date_trunc('day', $2::date)
            ORDER BY response_time ASC
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, dialogue_id, date_obj)
                #logging.info(f"Найдено {len(rows)} сообщений для диалога {dialogue_id} за {date_obj}")
                return [{"role": r["role"], "response": r["response"]} for r in rows]
        except Exception as e:
            logging.error(f"Ошибка get_messages_for_dialogue_for_date: {e}")
            return []

    async def upsert_conversation_summary(self, dialogue_id: int, summary: str):
        """
        Сохраняет (или обновляет) summary в таблице "Conversation" для указанного dialogue_id.
        Возвращает dialogue_id.
        """
        if not self.pool:
            logging.error("Нет подключения к базе данных")
            return None
        query = """
            INSERT INTO "Conversation"(dialogue_id, summary)
            VALUES ($1, $2)
            ON CONFLICT (dialogue_id) 
            DO UPDATE SET summary = EXCLUDED.summary
            RETURNING dialogue_id
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, dialogue_id, summary)
                return row["dialogue_id"]
        except Exception as e:
            logging.error(f"Ошибка upsert_conversation_summary: {e}")
            return None

