import logging
import nest_asyncio
import asyncio
from fastapi import FastAPI, Request
from gpt_service import GPTService
from summary_service import summarize_text
import config

nest_asyncio.apply()
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = FastAPI()
gpt_service = GPTService()

@app.post("/api/generate")
async def generate(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    logging.info(f"Received prompt: {prompt}")
    response_text = await gpt_service.predict(0, prompt)
    logging.info(f"Generated response: {response_text}")
    return {"response": response_text}

@app.post("/api/summarize")
async def summarize(request: Request):
    """
    Новый эндпоинт: принимает уже подготовленный текст диалога (dialog_text),
    прогоняет через summarize_text и возвращает результат.
    """
    data = await request.json()
    dialog_text = data.get("dialog_text", "")
    logging.info("Received text for summarization.")
    #summary = summarize_text(dialog_text)
    summary = await asyncio.to_thread(summarize_text, dialog_text)
    logging.info(f"Generated summary: {summary}")
    return {"summary": summary}

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting GPT API service...")
    uvicorn.run(app, host="0.0.0.0", port=9001)
