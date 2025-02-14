# from fastapi import FastAPI, Form
#
# from llama_service import DeepseekEngine
#
# app = FastAPI()
# deepseek_engine = DeepseekEngine()
#
# @app.get("/")
# def root():
#     return {"message": "Deepseek v3 API is running on CPU"}
#
# @app.post("/api/generate")
# async def generate(prompt: str = Form(...)):
#     response_text = deepseek_engine.predict(prompt)
#     return {"response": response_text}

from fastapi import FastAPI, Form
from llama_service import DeepSeekService

app = FastAPI()
deepseek_service = DeepSeekService()

@app.get("/")
def root():
    return {"message": "Llama-3.1-8B-Instruct API on CPU"}

@app.post("/api/generate")
async def generate(prompt: str = Form(...)):
    response_text = deepseek_service.predict(prompt)
    return {"response": response_text}
