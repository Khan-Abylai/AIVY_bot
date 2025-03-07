import logging
import openai
import config
import asyncio

logging.basicConfig(level=logging.INFO)

class GPTService:
    def __init__(self, model_name: str = "ft:gpt-4o-mini-2024-07-18:personal::B6jnvBba"):
        openai.api_key = config.GPT_API_KEY
        self.model_name = model_name
        self.user_contexts = {}
        self.lock = asyncio.Lock()

    async def predict(self, user_id: int, prompt: str) -> str:
        async with self.lock:
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = []
            self.user_contexts[user_id].append({"role": "user", "content": prompt})
            messages = [{"role": "system", "content": "You are a friendly psychological assistant AIvy who helps users by providing practical solutions without repetitive questions."}] + self.user_contexts[user_id][-5:]
            try:
                response = await openai.ChatCompletion.acreate(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.5,
                    presence_penalty=0.2,
                    frequency_penalty=0.2
                )
                answer = response["choices"][0]["message"]["content"]
                self.user_contexts[user_id].append({"role": "assistant", "content": answer})
                return answer
            except Exception as e:
                logging.error(f"Error generating response: {e}")
                return "Извините, произошла ошибка. Попробуйте снова позже."

    def reset_context(self, user_id: int):
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
