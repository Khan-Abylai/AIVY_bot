from fastapi import FastAPI, Form
from gpt_service import GPTService

app = FastAPI()
gpt_service = GPTService()

@app.get("/")
def root():
    return {"message": "GPT Model API Service"}

@app.post("/api/generate")
async def generate(prompt: str = Form(...)):
    """
    Эндпоинт для генерации ответа модели по переданному prompt.
    Ожидается, что prompt передаётся в теле запроса в виде form-data.
    """
    response_text = gpt_service.predict(prompt)
    return {"response": response_text}
