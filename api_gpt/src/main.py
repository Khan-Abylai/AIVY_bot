from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import tiktoken

import config
from gpt_service import GPTService
from memory_service import MemoryService

# ───── settings & constants
RESERVED_TOKENS         = 800
HISTORY_SUMMARY_THRESHOLD = 40
CHUNK_TOKEN_LIMIT       = 1_500

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ───── services
app     = FastAPI(title="AIVY-GPT API", version="1.4")
service = GPTService()
memory  = MemoryService()

# ──────────────────────────────────────────────────────────── helpers
def tokenizer(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def ctx_limit(model: str) -> int:
    if model.endswith("16k"):
        return 16_384
    if model.startswith("gpt-4") or "4o" in model:
        return 128_000
    return 4_096

def active_prompt_and_model(session_id: str) -> tuple[str, str]:
    module = memory.get_module(session_id)
    return (
        config.ANALYZER_SYSTEM_PROMPT_M2
        if module == 2
        else config.ANALYZER_SYSTEM_PROMPT,
        config.ANALYZER_MODEL_M2
        if module == 2
        else config.ANALYZER_MODEL,
    )

def trim_history(
    system_prompt: str,
    history: List[Dict[str, str]],
    tok,
    model: str,
) -> List[Dict[str, str]]:
    """Сдвигаем окно так, чтобы (история+зарезерв) ≤ контекст."""
    cap   = ctx_limit(model)
    total = len(tok.encode(system_prompt))
    cut   = []

    # добавляем history с конца (самые новые) ← более дёшево, O(N)
    for msg in reversed(history):
        n = len(tok.encode(msg["content"]))
        if total + n + RESERVED_TOKENS > cap:
            break
        cut.append(msg)
        total += n

    return [{"role": "system", "content": system_prompt}] + list(reversed(cut))

def split_into_chunks(text: str, limit: int, model: str):
    """Генератор чанков по token-limit."""
    tok = tokenizer(model)
    ids = tok.encode(text)
    for i in range(0, len(ids), limit):
        yield tok.decode(ids[i : i + limit])

async def retry_predict(*, model: str, messages: list,
                        max_tokens=512, temperature=0.2,
                        attempts=4) -> str:
    delay = 5
    for idx in range(1, attempts + 1):
        try:
            return await service.predict(
                model_name=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            if "insufficient_quota" in str(exc).lower() or idx == attempts:
                raise
            #logger.warning("Retry after %s  (%d/%d)", exc, attempts+1, retries)
            logger.warning("GPT retry %d/%d after error: %s", idx, attempts, exc)
            await asyncio.sleep(delay)
            delay = min(delay*2, 60)

async def maybe_summarize(session_id: str):
    hist = memory.get_history(session_id)
    if len(hist) <= HISTORY_SUMMARY_THRESHOLD:
        return
    tok    = tokenizer(service.default_model)
    tokens = sum(len(tok.encode(m["content"])) for m in hist)
    if tokens < ctx_limit(service.default_model) * 0.6:
        return

    # Формируем промпт для краткой сводки
    prompt = "Кратко сформулируй содержание диалога:\n"
    prompt += "\n".join(f"{m['role']}: {m['content']}" for m in hist[:-HISTORY_SUMMARY_THRESHOLD])

    summary = await retry_predict(
        model=config.ANALYZER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )

    # Очищаем историю и добавляем сводку, затем восстанавливаем последние сообщения
    memory.clear_history(session_id)
    memory.append_message(session_id, "system_summary", summary)
    for m in hist[-HISTORY_SUMMARY_THRESHOLD:]:
        memory.append_message(session_id, m["role"], m["content"])

def make_session_id(user_id: Optional[str], cookie_sid: Optional[str], client_host: str) -> str:
    if user_id:
        return f"{user_id}-{datetime.utcnow().date()}"
    return cookie_sid or client_host

async def get_payload(req: Request):
    if req.headers.get("content-type", "").startswith("application/json"):
        return await req.json()
    return await req.form()

# ──────────────────────────────────────────────────────────── endpoints
@app.post("/api/generate")
async def generate_chat(request: Request):
    payload     = await get_payload(request)
    user_input  = (payload.get("user_input") or payload.get("prompt") or "").strip()
    if not user_input:
        raise HTTPException(422, "Не передано поле 'user_input' / 'prompt'.")

    session_id = make_session_id(
        payload.get("user_id"),
        payload.get("session_id") or request.cookies.get("session_id"),
        request.client.host,
    )
    logger.info("Session %s | Input len %d", session_id, len(user_input))

    # 1) суммаризация истории при необходимости
    await maybe_summarize(session_id)

    replies: list[str] = []
    for chunk in split_into_chunks(user_input, CHUNK_TOKEN_LIMIT, service.default_model):
        memory.append_message(session_id, "user", chunk)

        # 2) выбираем prompt/model под активный модуль
        sys_prompt, model = active_prompt_and_model(session_id)

        history   = memory.get_history(session_id)
        summary   = next((m for m in history if m["role"] == "system_summary"), None)
        if summary:
            sys_prompt += f"\n\nСводка: {summary['content']}"

        tok       = tokenizer(model)
        messages  = trim_history(sys_prompt, history, tok, model)

        print(f" - messages: {messages}")

        # 3) вызываем модель
        reply = await retry_predict(model=model,
                                    messages=messages,
                                    max_tokens=256)

        if reply.lower().startswith("переход") and "модул" in reply.lower():
            logger.info("Session %s → switch to Module-2", session_id)
            memory.set_module(session_id, 2)
            sys_prompt, model = active_prompt_and_model(session_id)
            messages = trim_history(sys_prompt, memory.get_history(session_id), tok, model)
            reply = await retry_predict(model=model,
                                        messages=messages,
                                        max_tokens=256)

            print(f" - new messages: {messages}")

        memory.append_message(session_id, "assistant", reply)
        replies.append(reply)

    response_text = "\n".join(replies)
    logger.debug("Response: %s…", response_text[:120])

    resp = JSONResponse({"session_id": session_id, "response": response_text})
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@app.post("/api/clear")
async def clear_history(request: Request):
    sid = (await request.json()).get("session_id")
    if not sid:
        raise HTTPException(400, "session_id не предоставлен")
    memory.clear_history(sid)
    return {"session_id": sid, "message": "История очищена"}
