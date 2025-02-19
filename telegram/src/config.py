import os

TOKEN = os.environ.get("TELEGRAM_TOKEN", "7400358963:AAEeeRdwLBfxEXp44E-awnTMEcliYrUOQOo")

# URL для GPT API
GPT_API_URL = os.environ.get("GPT_API_URL", "http://gpt_api:9001/api/generate")

# PostgreSQL конфигурация
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "gpt_db")
DB_USER = os.getenv("DB_USER", "gpt_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gpt_password")