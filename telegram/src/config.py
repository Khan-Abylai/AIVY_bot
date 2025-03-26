import os

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TOKEN:
    print("TELEGRAM_TOKEN не найден в переменных окружения.")
else:
    print("TELEGRAM_TOKEN успешно загружен.")

GPT_API_URL = os.getenv("GPT_API_URL", "")
if not GPT_API_URL:
    print("GPT_API_URL не найден в переменных окружения.")
else:
    print("GPT_API_URL успешно загружен.")

# Новый URL для эндпоинта суммаризации.
SUMMARY_API_URL = os.getenv("SUMMARY_API_URL", "")
if not SUMMARY_API_URL:
    print("SUMMARY_API_URL не найден в переменных окружения.")
else:
    print("SUMMARY_API_URL успешно загружен.")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "gpt_db")
DB_USER = os.getenv("DB_USER", "gpt_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gpt_password")

summary_start_sleep_time = 120  # c.
summary_update_loop_time = 120  # c.
