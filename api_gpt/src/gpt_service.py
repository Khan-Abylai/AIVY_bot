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
        self.default_model = default_model or config.ANALYZER_MODEL

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
        model = model_name or self.default_model

        if not messages and not prompt:
            logger.warning("Neither messages nor prompt were provided")
            return "Invalid input: no messages or prompt provided."

        generation_params: Dict[str, Any] = {
            "model": model,
            "temperature": temperature or config.GEN_PARAMS.get("temperature", 0.7),
            "presence_penalty": presence_penalty or config.GEN_PARAMS.get("presence_penalty", 0.0),
            "frequency_penalty": frequency_penalty or config.GEN_PARAMS.get("frequency_penalty", 0.0),
            "top_p": top_p or config.GEN_PARAMS.get("top_p", 1.0),
            "max_tokens": max_tokens or config.GEN_PARAMS.get("max_tokens", 512),
            "messages": messages or [
                {"role": "system", "content": config.ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt or ""},
            ],
        }

        try:
            filtered = [m for m in generation_params["messages"] if m["role"] in {"user", "assistant"}]
            log_str = "\n".join(f"{m['role']}: {m['content']}" for m in filtered)
            logger.info("[OpenAI History] %d messages\n%s", len(filtered), log_str)
        except Exception as log_err:
            logger.warning("Failed to log filtered messages: %s", log_err)

        try:
            response = await self.client.chat.completions.create(**generation_params)
            message = response.choices[0].message.content.strip()

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
