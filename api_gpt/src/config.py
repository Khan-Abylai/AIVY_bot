import os

GPT_API_KEY = os.getenv("GPT_API_KEY", "")

if not GPT_API_KEY:
    print("GPT_API_KEY не найден в переменных окружения.")
else:
    print("GPT_API_KEY успешно загружен.")
