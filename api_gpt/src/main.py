from __future__ import annotations

import asyncio
import difflib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import tiktoken
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import config
from gpt_service import GPTService
from memory_service import MemoryService

# ───── settings ───────────────────────────────────────────
RESERVED_TOKENS            = 300
HISTORY_SUMMARY_THRESHOLD  = 40
CHUNK_TOKEN_LIMIT          = 1_500
DUPLICATE_THRESHOLD        = 0.9     # similarity ratio
DUPLICATE_MAX_REPEATS      = 1       # сколько раз подряд допускаем дубль
TEMP_M0, TEMP_M2           = 0.2, 0.25
TEMP_DUPLICATE             = 0.45

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ───── services ───────────────────────────────────────────
app     = FastAPI(title="AIVY-GPT API", version="1.5")
service = GPTService()
memory  = MemoryService()

# ───── util: токенизатор + лимит окна ─────────────────────
def tokenizer(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def ctx_limit(model: str) -> int:
    if model.endswith("16k"):                   return 16_384
    if model.startswith(("gpt-4", "gpt-4o")):   return 128_000
    return 4_096

# ───── util: выбор prompt / model по модулю ───────────────
def active_prompt_and_model(session_id: str) -> tuple[str, str]:
    module = memory.get_module(session_id)
    return (
        config.ANALYZER_SYSTEM_PROMPT_M2, config.ANALYZER_MODEL_M2
    ) if module == 2 else (
        config.ANALYZER_SYSTEM_PROMPT,    config.ANALYZER_MODEL
    )

# ───── util: trim history (one-pass) ──────────────────────
def trim_history(system_prompt: str,
                 history: List[Dict[str, str]],
                 tok,
                 model: str) -> List[Dict[str, str]]:
    cap    = ctx_limit(model) - RESERVED_TOKENS
    budget = cap - len(tok.encode(system_prompt))
    kept: List[dict] = []

    for msg in reversed(history):
        if msg["role"] == "system_summary":
            continue
        cost = len(tok.encode(msg["content"]))
        if cost > budget:
            break
        kept.append(msg)
        budget -= cost

    kept.reverse()
    return [{"role": "system", "content": system_prompt}, *kept]

# ───── util: чанки длинного текста ────────────────────────
def split_into_chunks(text: str, limit: int, model: str):
    tok = tokenizer(model)
    ids = tok.encode(text)
    for i in range(0, len(ids), limit):
        yield tok.decode(ids[i:i + limit])

# ───── util: retry wrapper для GPT ────────────────────────
async def retry_predict(*, model: str, messages: list,
                        max_tokens=256, temperature=0.25,
                        attempts=4) -> str:
    delay = 5
    for attempt in range(1, attempts + 1):
        try:
            return await service.predict(
                model_name=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            if "insufficient_quota" in str(exc).lower() or attempt == attempts:
                raise
            logger.warning("GPT retry %d/%d: %s", attempt, attempts, exc)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

# ───── util: duplicate detection ──────────────────────────
def _normalize(txt: str) -> str:
    txt = re.sub(r"[^\w\s]", "", txt.lower())
    return re.sub(r"\s+", " ", txt).strip()

def is_similar(a: str, b: str, thr=DUPLICATE_THRESHOLD) -> bool:
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio() > thr

# ───── optional summary long history ──────────────────────
async def maybe_summarize(session_id: str):
    hist = memory.get_history(session_id)
    if len(hist) <= HISTORY_SUMMARY_THRESHOLD:
        return
    tok  = tokenizer(service.default_model)
    if sum(len(tok.encode(m["content"])) for m in hist) < ctx_limit(service.default_model) * 0.6:
        return

    prompt = "Кратко сформулируй содержание диалога:\n" + \
             "\n".join(f"{m['role']}: {m['content']}" for m in hist[:-HISTORY_SUMMARY_THRESHOLD])

    summary = await retry_predict(
        model=config.ANALYZER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256
    )

    # Очищаем историю и добавляем сводку, затем восстанавливаем последние сообщения
    memory.clear_history(session_id)
    memory.append_message(session_id, "system_summary", summary)
    for m in hist[-HISTORY_SUMMARY_THRESHOLD:]:
        memory.append_message(session_id, m["role"], m["content"])

# ───── util: session id helper ────────────────────────────
def make_session_id(user_id: Optional[str], cookie_sid: Optional[str], host: str) -> str:
    return f"{user_id}-{datetime.utcnow().date()}" if user_id else (cookie_sid or host)

async def get_payload(req: Request):
    if req.headers.get("content-type", "").startswith("application/json"):
        return await req.json()
    return await req.form()

# ───── FastAPI endpoints ─────────────────────────────────
@app.post("/api/generate")
async def generate_chat(request: Request):
    payload = await get_payload(request)
    user_input = (payload.get("user_input") or payload.get("prompt") or "").strip()
    if not user_input:
        raise HTTPException(422, "Не передано поле 'user_input' / 'prompt'.")

    session_id = make_session_id(
        payload.get("user_id"),
        payload.get("session_id") or request.cookies.get("session_id"),
        request.client.host,
    )
    logger.info("Session %s | len=%d", session_id, len(user_input))

    await maybe_summarize(session_id)

    repeat_count = 0  # подряд идущие дубли

    replies: list[str] = []
    for chunk in split_into_chunks(user_input, CHUNK_TOKEN_LIMIT, service.default_model):
        memory.append_message(session_id, "user", chunk)

        sys_prompt, model = active_prompt_and_model(session_id)

        history   = memory.get_history(session_id)
        summary   = next((m for m in history if m["role"] == "system_summary"), None)
        if summary:
            sys_prompt += f"\n\nСводка: {summary['content']}"

        # «меня зовут …»
        for m in history:
            if m["role"] == "user" and m["content"].lower().startswith("меня зовут"):
                name = m["content"].split()[-1].strip(".,!?\"")
                sys_prompt += f"\n\nИмя пользователя: {name}."
                break

        tok      = tokenizer(model)
        messages = trim_history(sys_prompt, history, tok, model)
        logger.debug("messages=%d", len(messages))

        temp = TEMP_M0 if memory.get_module(session_id) == 0 else TEMP_M2
        reply = await retry_predict(model=model,
                                    messages=messages,
                                    max_tokens=256,
                                    temperature=temp)

        # --- duplicate guard ---------------------------------
        last_assist = next((m for m in reversed(history) if m["role"] == "assistant"), None)
        if last_assist and is_similar(reply, last_assist["content"]):
            repeat_count += 1
            logger.debug("Duplicate %d for session %s", repeat_count, session_id)
            if repeat_count >= DUPLICATE_MAX_REPEATS:
                reply = await retry_predict(model=model,
                                            messages=messages,
                                            max_tokens=256,
                                            temperature=TEMP_DUPLICATE)
                repeat_count = 0
        else:
            repeat_count = 0
        # ------------------------------------------------------

        if reply.lower().startswith("переход") and "модул" in reply.lower():
            logger.info("Session %s → switch to Module-2", session_id)
            memory.set_module(session_id, 2)
            sys_prompt, model = active_prompt_and_model(session_id)
            messages = trim_history(sys_prompt, memory.get_history(session_id), tok, model)
            reply = await retry_predict(model=model,
                                        messages=messages,
                                        max_tokens=256,
                                        temperature=TEMP_M2)

        memory.append_message(session_id, "assistant", reply)
        replies.append(reply)

    resp = JSONResponse({
        "session_id": session_id,
        "response":   "\n".join(replies)
    })
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@app.post("/api/clear")
async def clear_history(request: Request):
    sid = (await request.json()).get("session_id")
    if not sid:
        raise HTTPException(400, "session_id не предоставлен")
    memory.clear_history(sid)
    return {"session_id": sid, "message": "История очищена"}
