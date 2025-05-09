from __future__ import annotations

import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime

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
    """
    Извлекает из запроса поля user_id, session_id и user_input (или prompt).
    Поддерживает JSON и form-data.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        return {
            "user_id":   data.get("user_id"),
            "session_id": data.get("session_id"),
            "user_input": data.get("user_input"),
        }
    else:
        form = await request.form()
        return {
            "user_id":   form.get("user_id"),
            "session_id": form.get("session_id"),
            "user_input": form.get("prompt") or form.get("user_input"),
        }

def split_text_into_chunks(text: str, max_tokens: int, model: str) -> List[str]:
    """Разбивает длинный текст на чанки по числу токенов."""
    tokenizer = tiktoken.encoding_for_model(model)
    tokens = tokenizer.encode(text)
    return [
        tokenizer.decode(tokens[i:i + max_tokens])
        for i in range(0, len(tokens), max_tokens)
    ]

async def summarize_history_if_needed(session_id: str):
    """
    Если история для session_id слишком длинная, суммирует старую часть,
    оставляя недавние сообщения для контекста.
    """
    history = memory.get_history(session_id)
    if len(history) <= HISTORY_SUMMARY_THRESHOLD:
        return

    # Берём всё кроме последних HISTORY_SUMMARY_THRESHOLD сообщений
    to_summarize = history[:-HISTORY_SUMMARY_THRESHOLD]
    prompt = "Сформулируй кратко содержание предыдущего диалога:\n"
    for msg in to_summarize:
        prompt += f"{msg['role']}: {msg['content']}\n"

    summary = await service.predict(
        model_name=config.ANALYZER_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    # Очищаем историю и добавляем сводку, затем восстанавливаем последние сообщения
    memory.clear_history(session_id)
    memory.append_message(session_id, "system_summary", summary)
    for msg in history[-HISTORY_SUMMARY_THRESHOLD:]:
        memory.append_message(session_id, msg["role"], msg["content"])

# Endpoints
@app.post("/api/generate")
async def generate_chat(request: Request):
    # Парсим входные данные
    parsed     = await parse_request(request)
    user_id    = parsed.get("user_id")
    body_sess  = parsed.get("session_id")
    user_input = (parsed.get("user_input") or "").strip()

    if not user_input:
        raise HTTPException(status_code=422, detail="Поле 'user_input' или 'prompt' не предоставлено.")

    # Формируем session_id: если есть user_id — привязываем по дате, иначе — из тела/куки/host
    cookie_sess = request.cookies.get("session_id")
    if user_id is not None:
        # Обновляется раз в сутки
        today = datetime.utcnow().date().isoformat()
        session_id = f"{user_id}-{today}"
    else:
        session_id = body_sess or cookie_sess or request.client.host

    logger.info("Session %s | Input len %d", session_id, len(user_input))

    # При необходимости делаем суммирование истории
    await summarize_history_if_needed(session_id)

    # Разбиваем пользовательский ввод на чанки
    chunks: List[str] = split_text_into_chunks(user_input, CHUNK_TOKEN_LIMIT, service.default_model)
    responses: List[str] = []

    for chunk in chunks:
        # Сохраняем вопрос пользователя
        memory.append_message(session_id, "user", chunk)
        history = memory.get_history(session_id)

        # Строим системный prompt
        system_prompt = config.ANALYZER_SYSTEM_PROMPT
        # Если есть сводка — включаем её
        for msg in history:
            if msg["role"] == "system_summary":
                system_prompt += f"\n\nСводка: {msg['content']}"
                break

        # Автоматически выделяем имя пользователя, если было сказано "меня зовут ..."
        user_name: Optional[str] = None
        for msg in history:
            if msg["role"] == "user" and msg["content"].lower().startswith("меня зовут"):
                parts = msg["content"].split()
                if len(parts) >= 3:
                    user_name = parts[-1].strip(".,!?\"")
                break
        if user_name:
            system_prompt += f"\n\nИмя пользователя: {user_name}. Обращайся по имени."

        # Собираем сообщения для API
        messages = [{"role": "system", "content": system_prompt}]
        messages += [
            {"role": m["role"], "content": m["content"]}
            for m in history if m["role"] != "system_summary"
        ]

        # Проверяем общий размер токенов
        tokenizer = tiktoken.encoding_for_model(service.default_model)
        total_tokens = sum(len(tokenizer.encode(m["content"])) for m in messages)
        if total_tokens + RESERVED_TOKENS > TOKEN_LIMIT:
            raise HTTPException(status_code=413, detail="Контекст слишком длинный. Начните новую сессию.")

        # Запрос в модель
        reply = await service.predict(model_name=config.ANALYZER_MODEL, messages=messages)
        memory.append_message(session_id, "assistant", reply)
        responses.append(reply)

    full_response = "\n".join(responses)

    # Возвращаем ответ и ставим куку с session_id
    result = {"session_id": session_id, "response": full_response}
    resp = JSONResponse(content=result)
    resp.set_cookie(key="session_id", value=session_id, httponly=True)
    return resp

@app.post("/api/clear")
async def clear_history(request: Request):
    """
    Очищает историю по переданному session_id.
    """
    data = await request.json()
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id не предоставлен.")
    memory.clear_history(session_id)
    return {"session_id": session_id, "message": "История очищена."}
