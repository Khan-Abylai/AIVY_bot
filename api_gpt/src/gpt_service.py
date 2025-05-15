import logging
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class GPTService:
    def __init__(self, default_model: Optional[str] = None) -> None:
        self.client = AsyncOpenAI(api_key=config.GPT_API_KEY)
        self.default_model = config.ANALYZER_MODEL

    async def predict(
        self,
        *,
        model_name: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        model = self.default_model or model_name

        # Проверяем, что хотя бы prompt или messages переданы
        if not messages and not prompt:
            logger.warning("Neither messages nor prompt were provided")
            return "Invalid input: no messages or prompt provided."

        # Гарантируем, что prompt — строка
        prompt = prompt or ""

        # Составляем параметры генерации
        generation_params: Dict[str, Any] = {
            "model": model,
            "temperature": temperature if temperature is not None else config.GEN_PARAMS.get("temperature", 0.7),
            "presence_penalty": presence_penalty if presence_penalty is not None else config.GEN_PARAMS.get("presence_penalty", 0.8),
            "frequency_penalty": frequency_penalty if frequency_penalty is not None else config.GEN_PARAMS.get("frequency_penalty", 0.9),
            "top_p": top_p if top_p is not None else config.GEN_PARAMS.get("top_p", 0.9),
            "max_tokens": max_tokens if max_tokens is not None else config.GEN_PARAMS.get("max_tokens", 512),
            "messages": messages if messages else [
                {"role": "system", "content": config.ANALYZER_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        }

        # Логирование пользовательских сообщений
        try:
            filtered = [m for m in generation_params["messages"] if m["role"] in {"user", "assistant"}]
            log_str = "\n".join(f"{m['role']}: {m['content']}" for m in filtered)
            logger.info("[OpenAI History] %d messages\n%s", len(filtered), log_str)
        except Exception as log_err:
            logger.warning("Failed to log filtered messages: %s", log_err)

        # Запрос к OpenAI
        try:
            response = await self.client.chat.completions.create(**generation_params)
            message = response.choices[0].message.content.strip()

            # Логирование токенов
            usage = getattr(response, "usage", None)
            if usage:
                logger.info(
                    "[Token Usage] prompt=%d | completion=%d | total=%d",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                )

            return message
        except Exception as e:
            logger.exception("OpenAI completion failed: %s", e)
            return "An error occurred while generating a response. Please try again later."
