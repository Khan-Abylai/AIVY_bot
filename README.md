# AIVY‑Bot

AIVY‑Bot — это микросервис из двух контейнеров:
 - api_gpt — FastAPI‑сервис, который общается с OpenAI‑моделью, ведёт долгую историю диалога и делает сжатия‑саммари.
 - telegram_bot — интерфейс в Telegram, пересылающий сообщения к api_gpt и возвращающий ответы пользователю.

---

## 1. Build containers

`make build_api_gpt` – соберёт образ FastAPI‑сервиса doc.aivy.kz/api_gpt:app из каталога api_gpt/.

`make build_bot` - соберёт образ Telegram‑бота doc.aivy.kz/telegram_bot:app из каталога telegram/.

```bash
make build_all
```

---

## 2. Run

```bash
make run
```

---
 
## 3. Stop / restart

```bash
make stop
```

``` bash
make restart
```

## 4. Запуск без Docker

### 1. Создать виртуальный env и установить зависимости
```bash
python3 -m venv .venv
```
```bash
pip install -r requirements.txt
```
```bash
source .venv/bin/activate
```

### 2. Запустить сервисы (два окна терминала)

#### - API‑GPT
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### - Telegram‑bot
```bash
python telegram/bot.py
```
