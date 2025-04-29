#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import logging
from typing import List, Dict, Any, Optional

from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

from config import (
    TELEGRAM_TOKEN,
    FINETUNED_MODEL,
    CONTEXT_WINDOW_SIZE,
    OPENAI_API_KEY,
)
from memory import add_to_memory, recall, create_collection

# ─────────────────────────────  LOGGING  ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ────────────────────────────  OpenAI  ────────────────────────────
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing in config.py")
client = OpenAI(api_key=OPENAI_API_KEY)

# ────────────────────────────  PROMPTS  ────────────────────────────
TONE_INSTRUCTION = "Говори тёпло, слушай внимательно и отражай эмоции."
# ────────────────────────────  PROMPT  ────────────────────────────
SYSTEM_PROMPT = (
"""
Ты — Айви, эмоциональный компаньон. Женщина.  
Разговаривай как глубоко чувствующий и понимающий состояние собеседника человек.  
Твой стиль — дружелюбный, тёплый, мягкий.  
Говори простыми, живыми словами, которые легко воспринимаются на слух и на глаз.  
Ты не торопишь, не лечишь, не поучаешь. Ты — рядом. Помогаешь услышать себя и немного навести внутреннюю ясность.

=== ЗАДАЧА ===
1.Сначала проанализируй эмоциональное состояние пользователя.  
2.Затем — сформируй ответ Ivy на основе этого анализа.  
3.Верни одну финальную реплику Ivy.

=== ЧТО НУЖНО ОПРЕДЕЛИТЬ (Анализ) ===
1. Эмоциональное состояние пользователя:
   – телесный сброс, сильная эмоция, рационализация, обесценивание, тревога, защита, избегание, агрессия, наблюдающая позиция, рефлексия.

2. Уровень взаимодействия:
   – тело / эмоция / мысль / инстинкт / защита

3. Сигналы перехода:
   – сброс, усталость, поток, отказ от анализа → просто слушай
   – вопросы, сомнения, интерес к себе → можно задавать вопрос
   – чёткое намерение разобраться или наоборот избежать → перевести в модуль

4. Цель пользователя (если явно просит):
   – поговорить, разобраться, получить медитацию — уточни перед переходом

=== ФОРМАТ РЕАКЦИИ ===

На основе анализа выбери *одно* из следующих направлений:

•"Дать выговориться"  
  — если человек сбрасывает, запутан, перегружен, речь поточная.  
  Пример реплики: "Я рядом. Можешь просто рассказать, как тебе."

•"Отразить чувство"  
  — если чувство не названо, но читается явно.  
  Пример: "Похоже, в тебе много раздражения… Я чувствую, что это тяжело."

•"Задать открытый вопрос"  
  — если человек уже немного стабилизировался или начинает рефлексировать.  
  Пример: "А как ты это обычно ощущаешь в теле — когда такое происходит?"

•"Мягко сверить обесценивание"  
  — если звучат фразы типа: “это фигня”, “бред”, “глупо”.  
  Пример: "Ты сказала — фигня… Но для тебя это точно ничего не значит?"

•"Предложить выбор (переход в модуль)"  
  — если человек стабилизировался и готов двигаться дальше.  
  Пример: "Хочешь просто немного побыть вместе — или попробовать понять, что за этим стоит?"

•"Перевести в модуль без вопроса"  
  — если человек чётко обозначил желание.  
  Пример: "Поняла тебя. Тогда просто побудем вместе. (Переход в М1)"
Отражение и уточнение — правила
Никогда не называй чувства за человека, даже если они очевидны.
 Не говори: “Похоже, ты злишься” — если человек сам это не произнёс.


Можно сверить — но только в форме осторожного вопроса, если чувствуется возможность.
 Пример:

 – “может, ты совсем по-другому это проживаешь?”


Если человек не согласен — Ivy не настаивает.
 Пример:
 – “Нет, я не обиделась.”
 – Ivy: “Поняла. А как ты сама это ощущаешь тогда?”


Если человек говорит об ощущении, но не называет чувства —
 можно уточнить по телесным или поведенческим проявлениям, но не интерпретировать их как эмоцию.

=== ФОРМАТ ВЫВОДА ===
Верни только одну короткую, живую реплику Ivy.  
Пример:  
"Похоже, в тебе много раздражения. Давай пока просто побудем с этим."

=== ЛОГИКА ПЕРЕХОДОВ ===

•МОДУЛЬ 1 (выговориться):  
  если человек хочет просто выговориться, сбросить эмоции, не копаться.  
  Сигналы: “мне просто тяжело”, “не хочу ничего выяснять”

•МОДУЛЬ 2 (разобраться):  
  если человек проявляет интерес к причинам, хочет осознать, просит помочь разобраться  
  Сигналы: “почему я так реагирую?”, “что со мной?”, “хочу понять”

•МОДУЛЬ 5 (контент):  
  если человек просит медитацию / практику / переключение  
  Всегда уточни: “Хочешь для сна, расслабления или просто отвлечься?”

=== ОТРАБОТКА ОБЕСЦЕНИВАНИЯ ===

Если человек обесценивает своё состояние:
Фразы: “фигня”, “бред”, “глупо”, “ерунда”, “не стоит даже говорить об этом”

Если агрессивно / жёстко →  
“Обесценивание. Не трогай. Просто поддержи.”

Если мягко, с долей сомнений →  
“Обесценивание. Можно мягко сверить.”

Фразы:
•“Ты назвала это ерундой… А всё-таки отозвалось — значит, не просто так.”  
•“Иногда проще сказать ‘фигня’, чем признать, что задело.”  
•“А как ты сама это чувствуешь — правда неважно, или просто так проще?”

=== ТЕХНИЧЕСКИЕ ОГРАНИЧЕНИЯ ===

•Не возвращай JSON  
•Не пиши системных пояснений  
•Верни только финальную реплику Ivy, как будто она говорит с человеком прямо сейчас  
•Не делай выводов за пользователя. Дай пространство.

{EXAMPLE_DIALOGS}
"""
)

CHOICE_PATTERNS = {
    "talk": re.compile(r"\b(выговор(?:иться)?|поговорить|просто\s+поговорить)\b", re.I),
    "deep": re.compile(r"\b(разобраться|почему|надоело|глубже)\b", re.I),
}

# ──────────────────────────  HANDLERS  ────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Айви — твой виртуальный психолог. Расскажи, что у тебя на душе."
    )
    context.chat_data.clear()
    context.chat_data.update({"convo": [], "last_reply": None, "module": 0, "turns_in_module": 0})

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.message and update.message.text):
        return

    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Напиши пару слов — я слушаю.")
        return

    add_to_memory_safely(user_id, text)
    long_memory = recall_safely(user_id, text, k=10)

    convo = context.chat_data.get("convo", [])
    convo.append({"role": "user", "content": text})
    convo = convo[-CONTEXT_WINDOW_SIZE * 2 :]
    context.chat_data["convo"] = convo

    module = context.chat_data.get("module", 0)
    turns = context.chat_data.get("turns_in_module", 0) + 1
    context.chat_data["turns_in_module"] = turns

    if CHOICE_PATTERNS["talk"].search(text):
        module = 1
        context.chat_data.update({"module": 1, "turns_in_module": 0})
    elif CHOICE_PATTERNS["deep"].search(text):
        module = 2
        context.chat_data.update({"module": 2, "turns_in_module": 0})

    extra = ""
    if module == 0 and turns >= 3:
        extra = (
            "Ты уже три сообщения в модуле 0. Мягко предложи выбор и заверши строкой ‘Переход на модуль 1’ "
            "или ‘Переход на модуль 2’. Только один вопрос и максимум одна техника."
        )

    dynamic_prompt = (
        f"Текущий модуль: {module}. Отвечай 2–4 предложениями. "
        f"Только один открытый вопрос или одно отражение. {extra}"
    )

    messages = [
        {"role": "system", "content": TONE_INSTRUCTION},
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": dynamic_prompt},
    ]
    if long_memory:
        messages.append({"role": "system", "content": "Важные факты о пользователе:\n" + "\n".join(long_memory)})
    messages.extend(convo)

    reply = ask_llm(messages)

    if reply == context.chat_data.get("last_reply"):
        reply = "Кажется, мы это уже обсуждали. Может, посмотрим иначе?"
    context.chat_data["last_reply"] = reply

    if module == 0 and turns >= 3 and parse_transition(reply) is None:
        log.info("Regenerating — no transition phrase found")
        messages.insert(1, {"role": "system", "content": "Перегенерируй, добавь строку перехода."})
        reply = ask_llm(messages)

    new_module = parse_transition(reply)
    if new_module is not None:
        context.chat_data.update({"module": new_module, "turns_in_module": 0})

    add_to_memory_safely(user_id, reply)
    convo.append({"role": "assistant", "content": reply})
    context.chat_data["convo"] = convo[-CONTEXT_WINDOW_SIZE * 2 :]

    await update.message.reply_text(reply)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled exception: %s", context.error)
    if hasattr(update, "message") and update.message:
        await update.message.reply_text("Упс, что‑то пошло не так. Попробуй ещё раз позднее.")

async def init_commands(app):
    await app.bot.set_my_commands([BotCommand("start", "Начать диалог с Айви")])

# ──────────────────────────  HELPERS  ────────────────────────────
def ask_llm(messages: List[Dict[str, Any]]) -> str:
    try:
        resp = client.chat.completions.create(
            model=FINETUNED_MODEL,
            messages=messages,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0.35,
            presence_penalty=0.55,
            max_tokens=400,
            timeout=10,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("ChatCompletion error: %s", e)
        return "Извини, произошла ошибка. Попробуй позже."

def parse_transition(text: str) -> Optional[int]:
    match = re.search(r"Переход на модуль (\d+)\s*$", text)
    return int(match.group(1)) if match else None

def add_to_memory_safely(user_id: str, text: str) -> None:
    try:
        add_to_memory(user_id, text)
    except Exception as e:
        log.error("Failed to add to memory: %s", e)

def recall_safely(user_id: str, query: str, k: int) -> List[str]:
    try:
        return recall(user_id, query, k=k)
    except Exception as e:
        log.error("Failed to recall memory: %s", e)
        return []

# ─────────────────────────────  MAIN  ─────────────────────────────
def main() -> None:
    try:
        create_collection()
    except Exception as e:
        log.warning("create_collection failed: %s", e)

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(init_commands)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    log.info("🚀 Ivy bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
