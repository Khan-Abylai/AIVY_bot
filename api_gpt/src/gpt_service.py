import logging
import openai
import config

logging.basicConfig(level=logging.INFO)

class GPTService:
    def __init__(self, model_name: str = "ft:gpt-4o-mini-2024-07-18:personal::B6jnvBba"):
        openai.api_key = config.GPT_API_KEY
        self.model_name = model_name

    def predict(self, prompt: str) -> str:
        messages = [
            {"role": "system",
             "content": "Ты — дружелюбный ассистент-психолог AIvy, который помогает пользователям, не переспрашивает одно и то же, старается не надоедать, и всегда предлагает практические решения для проблем."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                temperature=0.5,
                presence_penalty=0.2,
                frequency_penalty=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"


# if __name__ == "__main__":
#     service = GPTService()
#     test_prompt = "Привет! Как мне справиться со стрессом?"
#     answer = service.predict(test_prompt)
#     print("Ответ модели:", answer)
