from pathlib import Path
import os

# OpenAI API Key
GPT_KEY = ""
GPT_API_KEY: str = os.getenv("OPENAI_API_KEY", GPT_KEY)

# ───── settings ───────────────────────────────────────────
RESERVED_TOKENS            = 300
HISTORY_SUMMARY_THRESHOLD  = 200
SUMMARIZE_COUNT_MESSAGE    = 50
MAX_CTX_RATIO              = 0.8
CHUNK_TOKEN_LIMIT          = 1_500
DUPLICATE_THRESHOLD        = 0.9
DUPLICATE_MAX_REPEATS      = 1
TEMP_M0, TEMP_M2           = 0.2, 0.3
TEMP_DUPLICATE             = 0.45

# Default generation parameters
GEN_PARAMS = {
    "temperature": 0.5,
    "presence_penalty": 0.8,
    "frequency_penalty": 0.5,
    "top_p": 0.9,
    "max_tokens": 150,
}

ANALYZER_MODEL = "ft:gpt-4o-mini-2024-07-18:personal:aivy-pro-m1:BgaEwUob"
ANALYZER_MODEL_M2 = "ft:gpt-4o-mini-2024-07-18:personal:aivy-pro:Ba3Rra7J" # "gpt-4o"

PROMPTS_DIR = Path("/opt/api/prompts")

ANALYZER_SYSTEM_PROMPT    = (PROMPTS_DIR / "analyzer_system.txt").read_text("utf-8").strip()
ANALYZER_SYSTEM_PROMPT_M2 = (PROMPTS_DIR / "analyzer_system_m2.txt").read_text("utf-8").strip()
