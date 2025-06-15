from __future__ import annotations
import asyncio, difflib, logging, re
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

import tiktoken
from fastapi import Request

import config
logger = logging.getLogger(__name__)


def tokenizer(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def ctx_limit(model: str) -> int:
    if model.endswith("16k"):
        return 16_384
    if "gpt-4" in model or "gpt-4o" in model:
        return 128_000
    return 4_096

def make_session_id(user_id: Optional[str],
                    cookie_sid: Optional[str],
                    host: str) -> str:
    return f"{user_id}-{datetime.utcnow().date()}" if user_id else (cookie_sid or host)

async def get_payload(req: Request):
    if req.headers.get("content-type", "").startswith("application/json"):
        return await req.json()
    return await req.form()

def active_prompt_and_model(module) -> tuple[str, str]:
    return (
        config.ANALYZER_SYSTEM_PROMPT_M2, config.ANALYZER_MODEL_M2
    ) if module == 2 else (
        config.ANALYZER_SYSTEM_PROMPT,    config.ANALYZER_MODEL
    )

def trim_history(system_prompt: str,
                 history: List[Dict[str, str]],
                 tok,
                 model: str) -> List[Dict[str, str]]:
    cap    = ctx_limit(model) - config.RESERVED_TOKENS
    budget = cap - len(tok.encode(system_prompt))
    kept   = []

    for msg in reversed(history):
        cost = len(tok.encode(msg["content"]))
        if msg["role"] == "system_summary" and cost > budget:
            break
        if cost > budget:
            break
        kept.append(msg)
        budget -= cost

    kept.reverse()
    return [{"role": "system", "content": system_prompt}, *kept]

def split_into_chunks(text: str, limit: int, model: str):
    tok = tokenizer(model)
    ids = tok.encode(text)
    for i in range(0, len(ids), limit):
        yield tok.decode(ids[i:i + limit])

def _normalize(txt: str) -> str:
    txt = re.sub(r"[^\w\s]", "", txt.lower())
    return re.sub(r"\s+", " ", txt).strip()

def is_similar(a: str, b: str, thr=config.DUPLICATE_THRESHOLD) -> bool:
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio() > thr
