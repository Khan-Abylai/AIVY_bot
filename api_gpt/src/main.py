import logging
import nest_asyncio
import asyncio
from fastapi import FastAPI, Request
from gpt_service import GPTService
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

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting GPT API service...")
    uvicorn.run(app, host="0.0.0.0", port=9001)
