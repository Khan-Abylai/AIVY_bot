# gpt_service.py
import logging
from openai import AsyncOpenAI        # ← асинхронный клиент
import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class GPTService:
    def __init__(self, default_model: str | None = None):
        self.client = AsyncOpenAI(api_key=config.GPT_API_KEY)
        self.default_model = default_model or config.ANALYZER_MODEL

    async def predict(
        self,
        *,
        model_name: str | None = None,
        messages: list | None = None,
        prompt: str | None = None,
        temperature: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        model = model_name or self.default_model
        params = {
            "model": model,
            "temperature": temperature or config.GEN_PARAMS["temperature"],
            "presence_penalty": presence_penalty or config.GEN_PARAMS["presence_penalty"],
            "frequency_penalty": frequency_penalty or config.GEN_PARAMS["frequency_penalty"],
            "top_p": top_p or config.GEN_PARAMS["top_p"],
            "max_tokens": max_tokens or config.GEN_PARAMS["max_tokens"],
            "messages": messages
            if messages
            else [
                {"role": "system", "content": config.ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }

        snippet = params["messages"][-1]["content"][:100]
        logger.info("[Запрос OpenAI] модель=%s, фрагмент=%r", model, snippet)

        # Moderation API
        try:
            mod = await self.client.moderations.create(input=snippet)
            if mod.results[0].flagged:
                logger.warning("Модерация отклонила ввод")
                return (
                    "Извините, я не могу обсудить эту тему. "
                    "Обратитесь, пожалуйста, к специалисту."
                )
        except Exception as e:
            logger.error("Сбой Moderation API: %s — продолжаю без фильтра", e)

        # Chat completion
        try:
            resp = await self.client.chat.completions.create(**params)
            text = resp.choices[0].message.content.strip()
            usage = getattr(resp, "usage", None)
            if usage:
                logger.info(
                    "[Токены] prompt=%d, completion=%d, total=%d",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                )
            return text
        except Exception:
            logger.exception("Запрос OpenAI завершился ошибкой")
            return "К сожалению, при генерации ответа произошла ошибка. Попробуйте позже."
