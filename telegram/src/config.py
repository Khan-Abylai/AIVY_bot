import os

TOKEN = os.environ.get("TELEGRAM_TOKEN", "7400358963:AAEeeRdwLBfxEXp44E-awnTMEcliYrUOQOo")

# URL для стандартного API (Llama API)
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "http://parking:9001/api/generate")

# URL для GPT API
GPT_API_URL = os.environ.get("GPT_API_URL", "http://gpt_api:9002/api/generate")
