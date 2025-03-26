# api_gpt/summary_service.py
import torch
import config
from transformers import pipeline

# Определяем устройство (GPU или CPU)
device_number = 0 if torch.cuda.is_available() else -1

summarizer = pipeline(
    "summarization",
    model=config.model_summarizer,
    device=device_number
)

def summarize_text(dialog_text: str) -> str:
    """
    Получает длинный текст (весь диалог + предыдущие данные) и
    возвращает краткий пересказ (summary).
    """
    if not dialog_text.strip():
        return ""

    # Пример настройки параметров:
    result = summarizer(
        dialog_text,
        max_length=config.max_length,
        min_length=config.min_length,
        do_sample=config.do_sample
    )
    summary_text = result[0]["summary_text"].strip()
    return summary_text
