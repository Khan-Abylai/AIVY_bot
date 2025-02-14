# gpt_service.py
import logging
from openai import OpenAI
import config

logging.basicConfig(level=logging.INFO)

class GPTService:
    def __init__(self, model_name: str = "ft:gpt-4o-mini-2024-07-18:personal::B05i00tZ"):
        """
        Инициализирует клиента OpenAI с заданным API-ключом и именем модели.
        """
        self.client = OpenAI(api_key=config.GPT_API_KEY)
        self.model_name = model_name

    def predict(self, prompt: str) -> str:
        """
        Принимает строку prompt, формирует список сообщений для однократного запроса и
        возвращает ответ модели.
        """
        # Формируем сообщения с единственным сообщением от пользователя
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                presence_penalty=0.8,
                frequency_penalty=0.5
            )
            # Извлекаем текст ответа
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Ошибка при генерации ответа: {e}")
            return f"Ошибка: {str(e)}"
