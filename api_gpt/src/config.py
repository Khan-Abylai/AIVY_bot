import os

GPT_API_KEY = os.getenv("GPT_API_KEY", "")

if not GPT_API_KEY:
    print("GPT_API_KEY не найден в переменных окружения.")
else:
    print("GPT_API_KEY успешно загружен.")


# Настройки для GPTService
GPT_MODEL_NAME = os.getenv("GPT_MODEL_NAME", "ft:gpt-4o-mini-2024-07-18:personal::B7fitKw1")
GPT_TEMPERATURE = float(os.getenv("GPT_TEMPERATURE", 0.9))
GPT_PRESENCE_PENALTY = float(os.getenv("GPT_PRESENCE_PENALTY", 0.2))
GPT_FREQUENCY_PENALTY = float(os.getenv("GPT_FREQUENCY_PENALTY", 0.2))

# Параметры для работы с контекстом
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", 100))   # Максимальное число сообщений в истории до суммирования
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", 100))            # Число последних сообщений для формирования запроса

# Параметры суммаризации диалога
SUMMARY_MAX_TOKENS = int(os.getenv("SUMMARY_MAX_TOKENS", 150))
SUMMARY_MIN_TOKENS = int(os.getenv("SUMMARY_MIN_TOKENS", 50))
SUMMARY_TEMPERATURE = float(os.getenv("SUMMARY_TEMPERATURE", 0.5))
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "IlyaGusev/mbart_ru_sum_gazeta")

# Summarizer
model_summarizer = "IlyaGusev/mbart_ru_sum_gazeta"
max_length = 150
min_length = 50
do_sample = False
