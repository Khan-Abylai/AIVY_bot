import os
from pathlib import Path

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
# Fine‑tuned модель (после тренировки)
FINETUNED_MODEL: str = os.getenv("FINETUNED_MODEL", "ft:gpt-3.5-turbo-1106:personal:aivi-psybot-maxqc:BR7I4HXb")
# Путь к исходному JSON для fine‑tune
DATASET_JSON: Path = Path("/Users/aazamatov/Documents/AIVY/AIVY_bot/data_preprocessing/aivi_dialogues_dataset_2.json")
# Временный JSONL для загрузки в OpenAI
TRAIN_JSONL: Path = Path("../data_preprocessing/train_data_2.jsonl")

# Qdrant для RAG / память
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

# Telegram
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "7400358963:AAEeeRdwLBfxEXp44E-awnTMEcliYrUOQOo")
# Сколько последних сообщений держать в контексте
CONTEXT_WINDOW_SIZE: int = 15

RECENCY_ALPHA: float = 0.10
