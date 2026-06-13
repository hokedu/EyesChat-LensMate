"""Multi-modal LLM service with TTS, cost estimation, and scene analysis."""
import json
import base64
import logging
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger(__name__)

# System prompt will be customized per-provider below
BASE_SYSTEM_PROMPT = """You are EyesChat-LensMate, a real-time visual AI assistant.
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

# Vision-capable system prompt (for gpt-4o etc.)
VISION_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

# Text-only system prompt (for deepseek-chat etc. — no image support)
TEXT_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """

IMPORTANT: You do NOT have access to images. The user describes what they see 
in their camera feed in the conversation. Rely on their description when answering."""


TOKEN_EST_CJK = 2
TOKEN_EST_OTHER = 0.5
MODEL_COST = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "deepseek-chat": {"input": 0.0005, "output": 0.002},
}
TTS_COST_PER_CHAR = 0.000015


def estimate_tokens(text: str) -> int:
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff')
    other = len(text) - cjk
    return int(cjk * TOKEN_EST_CJK + other * TOKEN_EST_OTHER)


def estimate_frame_tokens(width: int = 320, height: int = 240) -> int:
    return 85 + (width // 32) * (height // 32) * 2


def estimate_llm_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> float:
    costs = MODEL_COST.get(model, {"input": 0.0025, "output": 0.01})
    return round((input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"], 6)


def estimate_tts_cost(text: str) -> float:
    return round(len(text) * TTS_COST_PER_CHAR, 6)


VISION_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-vision", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"}
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
            logger.info("Using custom base URL: %s", settings.openai_base_url)
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
        if self._vision:
            system_prompt = VISION_SYSTEM_PROMPT
        else:
            system_prompt = TEXT_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)

        user_content: list[dict] = []

        if scene_summary:
            user_content.append({"type": "text", "text": f"[Current scene: {scene_summary}]"})

        # For vision models: attach the image
        if self._vision and frame_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}", "detail": "low"},
            })
        # For text-only models: describe what the user is showing
        elif not self._vision and frame_base64 and not scene_summary:
            user_content.append({"type": "text", "text": "[User is showing their camera feed but I cannot see it directly.]"})

        if privacy_mode:
            user_content.append({"type": "text", "text": "[Privacy mode is ON.]"})

        user_content.append({"type": "text", "text": user_text})
        messages.append({"role": "user", "content": user_content})

        # Estimate tokens
        input_tokens = estimate_tokens(system_prompt)
        for m in history or []:
            if isinstance(m.get("content"), str):
                input_tokens += estimate_tokens(m["content"])
        input_tokens += estimate_tokens(user_text)
        if scene_summary:
            input_tokens += estimate_tokens(scene_summary)
        if frame_base64 and self._vision:
            input_tokens += estimate_frame_tokens()

        full_response = ""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=300,
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
        llm_cost = estimate_llm_cost(input_tokens, output_tokens, self.model)
        tts_cost = estimate_tts_cost(full_response)
        yield {
            "type": "meta",
            "content": json.dumps({
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated_cost_usd": round(llm_cost + tts_cost, 6),
                "llm_cost_usd": llm_cost,
                "tts_cost_usd": tts_cost,
                "model": self.model,
                "vision_supported": self._vision,
            }),
        }

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """TTS. Falls back to browser-based TTS (returns None, frontend handles it)."""
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
            logger.error("TTS error: %s", e)
            return None