import os

# Telegram Token
TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# GPT API URL
GPT_API_URL = os.getenv("GPT_API_URL", "")

# Проверка загруженных переменных
if not TOKEN:
    print("⚠️ TELEGRAM_TOKEN не найден в переменных окружения.")
else:
    print("✅ TELEGRAM_TOKEN успешно загружен.")

if not GPT_API_URL:
    print("⚠️ GPT_API_URL не найден в переменных окружения.")
else:
    print("✅ GPT_API_URL успешно загружен.")

# PostgreSQL конфигурация
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "gpt_db")
DB_USER = os.getenv("DB_USER", "gpt_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
