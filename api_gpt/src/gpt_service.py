import logging
import openai
import config
import asyncio

logging.basicConfig(level=logging.INFO)

class GPTService:
    def __init__(self, model_name: str = None):
        openai.api_key = config.GPT_API_KEY
        self.model_name = config.GPT_MODEL_NAME
        self.max_context_length = config.MAX_CONTEXT_LENGTH
        self.context_window = config.CONTEXT_WINDOW
        self.user_contexts = {}
        self.lock = asyncio.Lock()
        self.system_message = {
            "role": "system",
            "content": (
                "Ты — эмпатичный и внимательный ассистент-психолог AIvy. "
                "Помни, что в этом диалоге мы уже познакомились, ты знаешь имя собеседника и его текущие чувства. "
                "Используй всю историю диалога для формирования осмысленного и связного ответа. "
                "Отвечай детально, анализируя предыдущие реплики, и предлагай практические рекомендации."
            )
        }

    async def predict(self, user_id: int, prompt: str) -> str:
        async with self.lock:
            self.user_contexts.setdefault(user_id, []).append({"role": "user", "content": prompt})
            self._filter_duplicates(user_id)
            if len(self.user_contexts[user_id]) > self.max_context_length:
                await self._summarize_context(user_id)
            messages = [self.system_message] + self.user_contexts[user_id][-self.context_window:]
            try:
                response = await openai.ChatCompletion.acreate(
                    model=self.model_name,
                    messages=messages,
                    temperature=config.GPT_TEMPERATURE,
                    presence_penalty=config.GPT_PRESENCE_PENALTY,
                    frequency_penalty=config.GPT_FREQUENCY_PENALTY,
                    n=3
                )
                chosen_response = max(response["choices"], key=lambda c: len(c["message"]["content"]))
                answer = chosen_response["message"]["content"]
                self.user_contexts[user_id].append({"role": "assistant", "content": answer})
                return answer
            except Exception as e:
                logging.error(f"Error generating response: {e}")
                return "Извините, произошла ошибка. Попробуйте снова позже."

    def _filter_duplicates(self, user_id: int):
        msgs = self.user_contexts[user_id]
        filtered = []
        for msg in msgs:
            if filtered and filtered[-1]['role'] == msg['role'] and filtered[-1]['content'].strip().lower() == msg['content'].strip().lower():
                continue
            filtered.append(msg)
        self.user_contexts[user_id] = filtered

    async def _summarize_context(self, user_id: int):
        msgs = self.user_contexts[user_id]
        if len(msgs) <= self.max_context_length:
            return
        to_summarize = msgs[:-2]
        summary_prompt = "Сделай краткое резюме следующей беседы, сохраняя ключевые моменты и детали:\n\n" + "".join(
            f"{m['role']}: {m['content']}\n" for m in to_summarize
        )
        try:
            summary_response = await openai.ChatCompletion.acreate(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Ты ассистент, который умеет делать ёмкие и детальные сводки диалогов."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=config.SUMMARY_TEMPERATURE,
                max_tokens=config.SUMMARY_MAX_TOKENS
            )
            summary = summary_response["choices"][0]["message"]["content"]
            self.user_contexts[user_id] = [{"role": "assistant", "content": summary}] + msgs[-2:]
            logging.info(f"Context summarized for user {user_id}")
        except Exception as e:
            logging.error(f"Error summarizing context for user {user_id}: {e}")

    def reset_context(self, user_id: int):
        self.user_contexts.pop(user_id, None)
