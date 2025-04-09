import logging
import nest_asyncio
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from gpt_service import GPTService
import uvicorn

nest_asyncio.apply()
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
app = FastAPI()
gpt_service = GPTService()

class PredictRequest(BaseModel):
    user_id: int
    question: str

@app.post("/api-ai/predict")
async def predict_endpoint(payload: PredictRequest):
    logging.info(f"Received for user {payload.user_id}: {payload.question}")
    response_text = await gpt_service.predict(payload.user_id, payload.question)
    logging.info(f"Response for user {payload.user_id}: {response_text}")
    return {"response": response_text}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
