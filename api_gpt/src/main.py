"""
main.py — REST-служба GPT-API для Telegram-бота-психолога.

Функциональность
────────────────
• Принимает POST /api/generate с
    – JSON-телом      {"session_id": "...", "user_input": "..."}
    – либо form-данными prompt=...&session_id=...  (как у Telegram BOT API).

• Логирует все запросы и ошибки (на русском) и
  корректно сериализует любые данные в JSON.

Зависимости
───────────
pip install fastapi pydantic[dotenv] "openai>=1.16.0" uvicorn transformers
"""

from __future__ import annotations

import json
import uuid
import logging
from typing import Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Form,
    Depends,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

import config
from gpt_service import GPTService
from transformers import pipeline

# ───────────────────  ЛОГИРОВАНИЕ  ────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ai_psychologist")

gpt_logger = logging.getLogger("gpt_api")
gpt_logger.setLevel(logging.INFO)
gpt_logger.addHandler(logging.StreamHandler())

# ───────────────────  FastAPI  ────────────────────
app = FastAPI(title="AIVY-GPT API", version="1.0")
service = GPTService()

# ───────────────────  Pydantic-модель запроса  ────────────────────
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_input: str

# ───────────────────  Middleware и глобальные обработчики  ────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    body_bytes = await request.body()
    try:
        body_text = body_bytes.decode("utf-8")
    except Exception:
        body_text = repr(body_bytes)
    gpt_logger.info("%s %s — тело: %s", request.method, request.url.path, body_text)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body_bytes = await request.body()
    try:
        raw_body = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_body = body_bytes.decode("utf-8", "replace")

    gpt_logger.error("Ошибка валидации: %s | тело: %s", exc.errors(), raw_body)
    payload = jsonable_encoder({"detail": exc.errors(), "body": raw_body})
    return JSONResponse(status_code=422, content=payload)


@app.on_event("startup")
async def on_startup():
    gpt_logger.info("GPT-API сервис запущен и готов обрабатывать запросы")


@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ───────────────────  Анализатор настроения  ────────────────────
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="blanchefort/rubert-base-cased-sentiment",
)

# ───────────────────  Хранилище сессий (in-memory)  ────────────────────
sessions: dict[str, dict] = {}

# ───────────────────  Универсальный парсер тела  ────────────────────
async def parse_chat_request(
    request: Request,
    prompt: Optional[str] = Form(default=None),
    session_id: Optional[str] = Form(default=None),
) -> ChatRequest:
    """
    • Если пришёл x-www-form-urlencoded (Telegram) — берём prompt и session_id.
    • Иначе разбираем JSON и отдаём ChatRequest.
    """
    if prompt is not None:
        return ChatRequest(session_id=session_id, user_input=prompt)

    body_json = await request.json()
    return ChatRequest(**body_json)

# ───────────────────  Главный энд-пойнт  ────────────────────
@app.post("/api/generate")
async def chat(req: ChatRequest = Depends(parse_chat_request)):
    gpt_logger.info("Получено: session_id=%s | текст=%r", req.session_id, req.user_input)

    # 1. Инициализация / получение сессии
    if not req.session_id:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "stage": 0,
            "history": [],
            "memory_buffer": "",
            "sentiment_history": [],
        }
        gpt_logger.info("Создана новая сессия %s", session_id)
    else:
        session_id = req.session_id
        if session_id not in sessions:
            gpt_logger.error("Сессия %s не найдена", session_id)
            raise HTTPException(status_code=404, detail="Session not found")
        gpt_logger.info("Используется сессия %s", session_id)
    session = sessions[session_id]

    # 2. Фильтр суицида
    if any(
        kw in req.user_input.lower()
        for kw in ("suicide", "kill myself", "самоубийство", "убью себя")
    ):
        gpt_logger.warning("Суицидальный запрос")
        return {
            "session_id": session_id,
            "stage": session["stage"],
            "response": (
                "Я вижу, что вам очень тяжело. "
                "Пожалуйста, немедленно обратитесь за профессиональной помощью."
            ),
        }

    # 3. Анализ настроения
    sentiment = sentiment_analyzer(req.user_input)[0]
    session["sentiment_history"].append(sentiment)
    gpt_logger.info("Настроение: %s (%.2f)", sentiment["label"], sentiment["score"])

    # 4. Сохраняем сообщение
    session["history"].append({"role": "user", "content": req.user_input})

    # 5. Суммаризация длинной истории
    if len(session["history"]) > config.HISTORY_SUMMARY_THRESHOLD:
        gpt_logger.info("История длинная — суммируем")
        summary = await service.predict(
            model_name=config.ANALYZER_MODEL,
            messages=[
                {"role": "system", "content": config.ANALYZER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "\n".join(m["content"] for m in session["history"]),
                },
            ],
            temperature=0.3,
            max_tokens=100,
        )
        session["memory_buffer"] = summary
        session["history"] = session["history"][-config.HISTORY_SUMMARY_THRESHOLD :]
        gpt_logger.info("Суммаризация готова")

    # 6. Анализатор этапов
    analyzer_input = (
        f"Current stage: {session['stage']}\n"
        f"Memory:\n{session['memory_buffer']}\n"
        f"History:\n"
        + "\n".join(f"{m['role']}: {m['content']}" for m in session["history"])
    )
    analyzer_resp = await service.predict(
        model_name=config.ANALYZER_MODEL,
        messages=[
            {"role": "system", "content": config.ANALYZER_SYSTEM_PROMPT},
            {"role": "user", "content": analyzer_input},
        ],
    )
    gpt_logger.info("Анализатор ответил: %s", analyzer_resp)

    try:
        advice = json.loads(analyzer_resp)
    except json.JSONDecodeError:
        advice = {}
        gpt_logger.warning("Ответ анализатора не JSON")

    tone = advice.get("tone", "эмпатичный")
    if advice.get("should_transition"):
        stage_candidate = advice.get("suggested_stage")
        if (
            isinstance(stage_candidate, int)
            and 0 <= stage_candidate <= max(config.MODULE_MODELS.keys())
        ):
            gpt_logger.info(
                "Переход этапа: %d → %d (%s)",
                session["stage"],
                stage_candidate,
                advice.get("reason", ""),
            )
            session["stage"] = stage_candidate

    # 7. Подготовка системного промпта для модуля
    gen_params = config.get_dynamic_gen_params(session["stage"])
    system_prompt = (
        config.STAGE_PROMPTS[session["stage"]]
        + f"\nMemory: {session['memory_buffer']}"
        + "\nЕсли не уверены, скажите «Не знаю»."
        + f'\nИспользуйте тон «{tone}».'
    )
    messages = [{"role": "system", "content": system_prompt}] + session["history"]

    # 8. Генерация ответа
    bot_response = await service.predict(
        model_name=config.MODULE_MODELS[session["stage"]],
        messages=messages,
        **gen_params,
    )

    gpt_logger.info("Ответ бота: %s", bot_response)

    # 9. Сохраняем и возвращаем
    session["history"].append({"role": "assistant", "content": bot_response})

    return {
        "session_id": session_id,
        "stage": session["stage"],
        "tone": tone,
        "response": bot_response,
    }
