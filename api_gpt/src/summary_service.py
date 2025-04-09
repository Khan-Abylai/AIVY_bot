# api_gpt/summary_service.py
import torch
import config
from transformers import pipeline

device_number = 0 if torch.cuda.is_available() else -1

summarizer = pipeline(
    "summarization",
    model=config.SUMMARY_MODEL,
    device=device_number
)

def summarize_text(dialog_text: str) -> str:

    if not dialog_text.strip():
        return ""

    result = summarizer(
        dialog_text,
        max_length=config.SUMMARY_MAX_TOKENS,
        min_length=config.SUMMARY_MIN_TOKENS,
        do_sample=config.SUMMARY_TEMPERATURE
    )
    summary_text = result[0]["summary_text"].strip()
    return summary_text
