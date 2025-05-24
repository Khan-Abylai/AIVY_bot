from __future__ import annotations
import logging, asyncio
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import tiktoken

import config                                 # ANALYZER_MODEL = "ft:…"
from gpt_service import GPTService
from memory_service import MemoryService

# ───── constants
RESERVED_TOKENS = 800
HISTORY_SUMMARY_THRESHOLD = 40
CHUNK_TOKEN_LIMIT = 1_500

# ───── logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("aivy_api")

# ───── services
app = FastAPI(title="AIVY-GPT with Persistent Context", version="1.3")
service = GPTService()          # .default_model хранит ID дефолтной модели
memory = MemoryService()

# ───── helpers
def get_prompt_model(session_id: str):
    """
    Возвращает (system_prompt, model_id) в зависимости от активного модуля
    0 – вход, 2 – «разобраться».
    """
    module = memory.get_module(session_id)          # <= добавлено
    print(" ---------- module", module, module == 2)
    if module == 2:
        return config.ANALYZER_SYSTEM_PROMPT_M2, config.ANALYZER_MODEL_M2
    return config.ANALYZER_SYSTEM_PROMPT,          config.ANALYZER_MODEL

def get_tokenizer(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def model_ctx_limit(model: str) -> int:
    if model.endswith("16k"):
        return 16_384
    if model.startswith("gpt-4") or "4o" in model:
        return 128_000
    return 4_096

def trim_history_to_fit(sys_prompt: str,
                        history: List[Dict[str,str]],
                        tok,
                        model: str) -> List[Dict[str,str]]:
    """Удаляет самые старые сообщения, пока не впишемся в окно модели."""
    cap = model_ctx_limit(model)
    while True:
        msgs = [{"role": "system", "content": sys_prompt}] + \
               [m for m in history if m["role"] != "system_summary"]
        total = sum(len(tok.encode(m["content"])) for m in msgs)
        if total + RESERVED_TOKENS <= cap:
            return msgs

        # если summary уже есть  → удаляем старейший non-summary
        if any(m["role"] == "system_summary" for m in history):
            for i, m in enumerate(history):
                if m["role"] != "system_summary":
                    history.pop(i)
                    break
        else:
            # summary ещё нет → создаём «заглушку»
            history.insert(0,
                {"role": "system_summary", "content": "Краткая сводка предыдущего диалога."})

async def parse_request(req: Request) -> Dict[str, Optional[str]]:
    if req.headers.get("content-type", "").startswith("application/json"):
        data = await req.json()
    else:
        data = await req.form()
    return {
        "user_id":   data.get("user_id"),
        "session_id": data.get("session_id"),
        "user_input": data.get("user_input") or data.get("prompt"),
    }

def split_text_into_chunks(text: str, limit: int, model: str) -> List[str]:
    """Разбивает длинный текст на чанки по числу токенов."""
    tok = get_tokenizer(model)
    ids = tok.encode(text)
    chunks = [tok.decode(ids[i:i + limit]) for i in range(0, len(ids), limit)]
    logger.debug(" -- split-chunks=%d", len(chunks))
    return chunks

async def safe_predict(*, model_name: str, messages: list,
                       max_tokens=512, temperature=0.2, retries=4) -> str:
    delay = 5
    for attempt in range(retries):
        try:
            return await service.predict(model_name=model_name,
                                         messages=messages,
                                         max_tokens=max_tokens,
                                         temperature=temperature)
        except Exception as e:
            if "insufficient_quota" in str(e).lower() or attempt == retries-1:
                raise
            logger.warning("Retry after %s  (%d/%d)", e, attempt+1, retries)
            await asyncio.sleep(delay)
            delay = min(delay*2, 60)

async def summarize_history_if_needed(session_id: str):
    hist = memory.get_history(session_id)
    if len(hist) <= HISTORY_SUMMARY_THRESHOLD:
        return
    tok = get_tokenizer(service.default_model)
    total = sum(len(tok.encode(m["content"])) for m in hist)
    if total < model_ctx_limit(service.default_model)*0.6:
        return

    prompt = "Сформулируй кратко содержание предыдущего диалога:\n"
    for m in hist[:-HISTORY_SUMMARY_THRESHOLD]:
        prompt += f"{m['role']}: {m['content']}\n"

    summary = await safe_predict(model_name=config.ANALYZER_MODEL,
                                 messages=[{"role": "user", "content": prompt}],
                                 max_tokens=256)

    # Очищаем историю и добавляем сводку, затем восстанавливаем последние сообщения
    memory.clear_history(session_id)
    memory.append_message(session_id, "system_summary", summary)
    for m in hist[-HISTORY_SUMMARY_THRESHOLD:]:
        memory.append_message(session_id, m["role"], m["content"])

# ───── endpoints
@app.post("/api/generate")
async def generate_chat(request: Request):
    p = await parse_request(request)
    user_input = (p["user_input"] or "").strip()
    if not user_input:
        raise HTTPException(422, "Поле 'user_input' / 'prompt' не предоставлено")

    cookie_sid = request.cookies.get("session_id")
    if p["user_id"]:
        session_id = f"{p['user_id']}-{datetime.utcnow().date()}"
    else:
        session_id = p["session_id"] or cookie_sid or request.client.host

    logger.info("Session %s | Input len %d", session_id, len(user_input))

    # При необходимости делаем суммирование истории
    await summarize_history_if_needed(session_id)

    chunks  = split_text_into_chunks(user_input, CHUNK_TOKEN_LIMIT,
                                     service.default_model)
    replies : list[str] = []

    for chunk in chunks:
        # Сохраняем вопрос пользователя
        memory.append_message(session_id, "user", chunk)
        history = memory.get_history(session_id)

        # system prompt
        #system_prompt = config.ANALYZER_SYSTEM_PROMPT
        # prompt + модель по номеру модуля
        system_prompt, model_id = get_prompt_model(session_id)
        if (s := next((m for m in history if m["role"]=="system_summary"), None)):
            system_prompt += f"\n\nСводка: {s['content']}"

        # имя пользователя
        for m in history:
            if m["role"]=="user" and m["content"].lower().startswith("меня зовут"):
                name = m["content"].split()[-1].strip(".,!?\"")
                system_prompt += f"\n\nИмя пользователя: {name}."
                break

        tok = get_tokenizer(service.default_model)
        messages = trim_history_to_fit(system_prompt, history, tok,
                                       service.default_model)

        logger.debug("messages=%d  tokens=%d",
                     len(messages),
                     sum(len(tok.encode(m["content"])) for m in messages))
        print(f" - messages: {messages}")

        # reply = await safe_predict(model_name=config.ANALYZER_MODEL,
        #                            messages=messages,
        #                            max_tokens=512)  # 256
        reply = await safe_predict(model_name=model_id,
                                   messages=messages,
                                   max_tokens=512)  # 256

        if reply.strip().lower().startswith("переход") and "модул" in reply.lower():
            logger.info("Session %s → switch to Module-2", session_id)

            memory.set_module(session_id, 2)  # фиксируем модуль
            # заново берём prompt + модель для М2
            system_prompt, model_id = get_prompt_model(session_id)
            history = memory.get_history(session_id)

            tok = get_tokenizer(service.default_model)
            messages = trim_history_to_fit(system_prompt, history, tok, service.default_model)
            messages.append({
                            "role": "system",
                            "content": ANALYZER_SYSTEM_TRANSITION_M2
                            })

            print(f" - new messages: {messages}")

            reply = await safe_predict(model_name=model_id,
                                       messages=messages,
                                       max_tokens=512)  # 256
            print(" - reply", reply)

        memory.append_message(session_id, "assistant", reply)
        replies.append(reply)

    print(f" - replies: {replies}")
    full = "\n".join(replies)
    logger.debug("response: %s", full[:120])

    res = {"session_id": session_id, "response": full}
    resp = JSONResponse(res)
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@app.post("/api/clear")
async def clear_history(request: Request):
    data = await request.json()
    sid = data.get("session_id")
    if not sid:
        raise HTTPException(400, "session_id не предоставлен")
    memory.clear_history(sid)
    return {"session_id": sid, "message": "История очищена."}
