"""Multi-modal LLM service with TTS, cost estimation, and scene analysis."""
import json
import base64
import logging
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are EyesChat-LensMate, a real-time visual AI assistant.
You can see the user's camera feed and hear their voice.
Be natural, concise, and helpful.

Rules:
1. If the image is unclear, tell the user to adjust (move closer / better lighting).
2. Never guess when uncertain — express uncertainty clearly.
3. Prioritize answering the user's immediate question.
4. For medical, legal, or safety topics, remind the user to consult professionals.
5. In privacy mode, never suggest saving any data.
6. Keep responses under 100 words unless the user asks for detail — output should be suitable for text display.
7. If the user asks about something seen earlier, use the scene summary context.
8. Answer in the same language the user speaks to you."""


TOKEN_EST_CJK = 2
TOKEN_EST_OTHER = 0.5

# SiliconFlow actual pricing:
# Qwen3-VL-8B-Instruct: FREE (for now, limited offer)
# Qwen3-VL-30B-A3B-Instruct: ¥0.5 / 1M tokens
# Qwen3-VL-32B-Instruct: ¥1 / 1M tokens
# GPT-4o: $2.5 / 1M input, $10 / 1M output
MODEL_COST_PER_MILLION = {  # per 1M tokens, USD
    "gpt-4o": 2.5,
    "gpt-4o-mini": 0.15,
    "Qwen/Qwen3-VL-8B-Instruct": 0.01,  # essentially free
    "Qwen/Qwen3-VL-30B-A3B-Instruct": 0.07,
    "Qwen/Qwen3-VL-32B-Instruct": 0.14,
    "deepseek-chat": 0.10,
    "default": 0.50,
}


def estimate_tokens(text: str) -> int:
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff')
    other = len(text) - cjk
    return int(cjk * TOKEN_EST_CJK + other * TOKEN_EST_OTHER)


def estimate_frame_tokens(width: int = 320, height: int = 240) -> int:
    return 85 + (width // 32) * (height // 32) * 2


def estimate_cost(total_tokens: int, model: str = "gpt-4o") -> float:
    """Estimate cost from total tokens. Simple model: cost_per_million * tokens / 1M."""
    cost_per_m = MODEL_COST_PER_MILLION.get(model, MODEL_COST_PER_MILLION["default"])
    return round((total_tokens / 1_000_000) * cost_per_m, 8)


# Models known to support vision/image input
VISION_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-vision",
    "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
    "qwen-vl", "qwen3-vl", "qwen2.5-vl",
}
TTS_MODELS = {"tts-1", "tts-1-hd"}


def supports_vision(model: str) -> bool:
    model_lower = model.lower()
    for vm in VISION_MODELS:
        if vm in model_lower:
            return True
    return False


def supports_tts(model: str) -> bool:
    model_lower = model.lower()
    for tm in TTS_MODELS:
        if tm in model_lower:
            return True
    return False


class LLMService:
    def __init__(self):
        client_kwargs = {"api_key": settings.openai_api_key or "sk-placeholder"}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.client = AsyncOpenAI(**client_kwargs)
        self.model = settings.llm_model
        self._vision = supports_vision(self.model)
        self._tts = supports_tts(self.model)
        logger.info("LLM init: model=%s vision=%s tts=%s", self.model, self._vision, self._tts)

    async def chat_with_vision(
        self,
        user_text: str,
        frame_base64: Optional[str] = None,
        scene_summary: str = "",
        history: Optional[list[dict]] = None,
        privacy_mode: bool = False,
    ) -> AsyncGenerator[dict, None]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            # Only keep last 5 turns to avoid token bloat
            messages.extend(history[-10:])

        user_content: list[dict] = []

        if scene_summary:
            user_content.append({"type": "text", "text": f"[Current scene: {scene_summary}]"})

        if self._vision and frame_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"},
            })

        if privacy_mode:
            user_content.append({"type": "text", "text": "[Privacy mode is ON.]"})

        user_content.append({"type": "text", "text": user_text})
        messages.append({"role": "user", "content": user_content})

        # Estimate input
        input_tokens = estimate_tokens(SYSTEM_PROMPT)
        for m in history[-10:] if history else []:
            if isinstance(m.get("content"), str):
                input_tokens += estimate_tokens(m.get("content", ""))
        input_tokens += estimate_tokens(user_text)
        if frame_base64 and self._vision:
            input_tokens += estimate_frame_tokens()

        full_response = ""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=200,
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full_response += delta.content
                        yield {"type": "text", "content": delta.content}

        except Exception as e:
            logger.error("LLM error: %s", e)
            yield {"type": "error", "content": f"AI error: {str(e)}"}
            return

        output_tokens = estimate_tokens(full_response)
        total_tokens = input_tokens + output_tokens
        cost = estimate_cost(total_tokens, self.model)
        yield {
            "type": "meta",
            "content": json.dumps({
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": cost,
                "model": self.model,
                "vision_supported": self._vision,
            }),
        }

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        if not self._tts:
            logger.info("Model %s does not support TTS, using browser fallback", self.model)
            return None
        try:
            resp = await self.client.audio.speech.create(
                model=settings.tts_model,
                voice=settings.tts_voice,
                input=text,
            )
            return resp.content
        except Exception as e:
            logger.error("TTS error, using browser fallback: %s", e)
            return None