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
from utils import (
    tokenizer, ctx_limit, make_session_id, get_payload, is_similar,
    active_prompt_and_model, trim_history, split_into_chunks,
)

# ───── logging setup ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ───── services ───────────────────────────────────────────
app     = FastAPI(title="AIVY-GPT API", version="1.5")
service = GPTService()
memory  = MemoryService()


async def manage_history(
    session_id: str,
    model: str,
    *,
    max_messages: int = config.HISTORY_SUMMARY_THRESHOLD,
    summarize_count: int = config.SUMMARIZE_COUNT_MESSAGE,
    max_ctx_ratio: float = config.MAX_CTX_RATIO,
) -> None:
    tok      = tokenizer(model)
    limit    = ctx_limit(model)
    history  = memory.get_history(session_id)

    total_msgs = len(history)
    total_toks = sum(len(tok.encode(m["content"])) for m in history)

    if total_msgs <= summarize_count:
        return
    if total_msgs <= max_messages and total_toks <= limit * max_ctx_ratio:
        return

    num_to_summarize = max(1, total_msgs - summarize_count)
    chunk = history[:num_to_summarize]

    prev_summary = next(
        (m for m in history if m["role"] == "system" and m["content"].startswith("[summary]")),
        None
    )

    prompt_lines: List[str] = []
    if prev_summary:
        prompt_lines.append(f"{prev_summary['role']}: {prev_summary['content']}")
    prompt_lines += [f"{m['role']}: {m['content']}" for m in chunk]
    prompt = (
        "Суммируй диалог старых сообщени ниже в 5-15 предложениях "
        "учитывая предыдущую сводку(если есть), без потери ключевых фактов (имена, даты, решения, результат):\n\n"
        + "\n".join(prompt_lines)
    )

    summary = await service.retry_predict(
        model_name=config.ANALYZER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    new_history = [{"role": "assistant", "content": f"[summary]\n{summary}"}]
    new_history.extend(history[num_to_summarize:])

    memory.rewrite_history(session_id, new_history)
    logger.info(
        "Session %s: compressed last %d msgs into summary (tokens %d→%d)",
        session_id,
        num_to_summarize,
        total_toks,
        len(tok.encode(summary)),
    )

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

    logger.info("New request: session=%s | payload=%s", session_id, payload)

    repeat_count = 0
    replies: List[str] = []

    await manage_history(
        session_id,
        model=service.default_model
    )

    for chunk in split_into_chunks(user_input, config.CHUNK_TOKEN_LIMIT, service.default_model):
        memory.append_message(session_id, "user", chunk)

        sys_prompt, model = active_prompt_and_model(memory.get_module(session_id))

        history   = memory.get_history(session_id)
        summary   = next((m for m in history if m["role"] == "system_summary"), None)
        if summary:
            sys_prompt += f"\n\nСводка: {summary['content']}"

        for m in history:
            if m["role"] == "user" and m["content"].lower().startswith("меня зовут"):
                name = m["content"].split()[-1].strip(".,!?\"")
                sys_prompt += f"\n\nИмя пользователя: {name}."
                break

        tok      = tokenizer(model)
        messages = trim_history(sys_prompt, history, tok, model)
        logger.debug("Trimmed message count: %d", len(messages))

        temp = config.TEMP_M0 if memory.get_module(session_id) == 0 else config.TEMP_M2
        reply = await service.retry_predict(
            model_name=model,
            messages=messages,
            temperature=temp
        )
        logger.info("GPT Response: session=%s | model=%s - %sm | reply=%s", session_id, model, memory.get_module(session_id), reply)

        # duplicate guard...
        last_assist = next((m for m in reversed(history) if m["role"] == "assistant"), None)
        if last_assist and is_similar(reply, last_assist["content"]):
            repeat_count += 1
            if repeat_count >= config.DUPLICATE_MAX_REPEATS:
                reply = await service.retry_predict(
                    model_name=model,
                    messages=messages,
                    temperature=config.TEMP_DUPLICATE
                )
                repeat_count = 0
        else:
            repeat_count = 0

        if reply.lower().startswith("переход") and "модул" in reply.lower():
            logger.info("Session %s → switch to Module-2", session_id)
            memory.set_module(session_id, 2)
            sys_prompt, model = active_prompt_and_model(memory.get_module(session_id))
            messages = trim_history(sys_prompt, memory.get_history(session_id), tok, model)
            reply = await service.retry_predict(
                model_name=model,
                messages=messages,
                temperature=config.TEMP_M2
            )
            logger.info("GPT Response after module switch: session=%s | model=%s | reply=%s", session_id, model, reply)

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
    logger.info("Cleared history for session %s", sid)
    return {"session_id": sid, "message": "История очищена"}
