from __future__ import annotations

import uuid
import logging
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import tiktoken

import config
from gpt_service import GPTService
from memory_service import MemoryService

# Constants
TOKEN_LIMIT = 128000
RESERVED_TOKENS = 1000
HISTORY_SUMMARY_THRESHOLD = 40
CHUNK_TOKEN_LIMIT = 2000

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("aivy_api")

# Services
app = FastAPI(title="AIVY-GPT with Persistent Context", version="1.2")
service = GPTService()
memory = MemoryService()

# Helpers
async def parse_request(request: Request) -> Dict[str, Optional[str]]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        return {"session_id": data.get("session_id"), "user_input": data.get("user_input")}
    else:
        form = await request.form()
        return {"session_id": form.get("session_id"), "user_input": form.get("prompt") or form.get("user_input")}

def split_text_into_chunks(text: str, max_tokens: int, model: str) -> List[str]:
    tokenizer = tiktoken.encoding_for_model(model)
    tokens = tokenizer.encode(text)
    return [tokenizer.decode(tokens[i:i+max_tokens]) for i in range(0, len(tokens), max_tokens)]

async def summarize_history_if_needed(session_id: str):
    history = memory.get_history(session_id)
    if len(history) <= HISTORY_SUMMARY_THRESHOLD:
        return
    to_summarize = history[:-HISTORY_SUMMARY_THRESHOLD]
    prompt = "Сформулируй кратко содержание предыдущего диалога:\n"
    for msg in to_summarize:
        prompt += f"{msg['role']}: {msg['content']}\n"
    summary = await service.predict(model_name=config.ANALYZER_MODEL, messages=[{"role":"user","content":prompt}])
    memory.clear_history(session_id)
    memory.append_message(session_id, "system_summary", summary)
    for msg in history[-HISTORY_SUMMARY_THRESHOLD:]:
        memory.append_message(session_id, msg["role"], msg["content"])

# Endpoints
@app.post("/api/generate")
async def generate_chat(request: Request):
    # Parse input
    parsed = await parse_request(request)
    body_session = parsed.get("session_id")
    user_input = parsed.get("user_input")
    if not user_input:
        raise HTTPException(status_code=422, detail="Поле 'user_input' или 'prompt' не предоставлено.")

    # Determine session_id: body -> cookie -> new
    cookie_session = request.cookies.get("session_id")
    session_id = body_session or cookie_session or request.client.host
    user_input = user_input.strip()
    logger.info("Session %s | Input len %d", session_id, len(user_input))

    # Summarize if long
    await summarize_history_if_needed(session_id)

    # Chunking
    chunks = split_text_into_chunks(user_input, CHUNK_TOKEN_LIMIT, service.default_model)
    responses: List[str] = []

    for chunk in chunks:
        memory.append_message(session_id, "user", chunk)
        history = memory.get_history(session_id)

        # Build system prompt
        system_prompt = config.ANALYZER_SYSTEM_PROMPT
        for msg in history:
            if msg["role"] == "system_summary":
                system_prompt += f"\n\nСводка: {msg['content']}"
                break

        # Extract name
        user_name = None
        for msg in history:
            if msg["role"] == "user" and msg["content"].lower().startswith("меня зовут"):
                parts = msg["content"].split()
                if len(parts) >= 3:
                    user_name = parts[-1].strip(".,!?\"")
                break
        if user_name:
            system_prompt += f"\n\nИмя пользователя: {user_name}. Обращайся по имени."

        # Assemble messages
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history if m["role"] != "system_summary"]

        # Token check
        tokenizer = tiktoken.encoding_for_model(service.default_model)
        total_tokens = sum(len(tokenizer.encode(m["content"])) for m in messages)
        if total_tokens + RESERVED_TOKENS > TOKEN_LIMIT:
            raise HTTPException(status_code=413, detail="Контекст слишком длинный. Начните новую сессию.")

        # Call GPT
        reply = await service.predict(model_name=config.ANALYZER_MODEL, messages=messages)
        memory.append_message(session_id, "assistant", reply)
        responses.append(reply)

    full = "\n".join(responses)
    # Return with cookie
    result = {"session_id": session_id, "response": full}
    response = JSONResponse(content=result)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.post("/api/clear")
async def clear_history(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id не предоставлен.")
    memory.clear_history(session_id)
    return {"session_id": session_id, "message": "История очищена."}
