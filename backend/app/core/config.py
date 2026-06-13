"""EyesChat-LensMate config."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "EyesChat-LensMate"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Session control
    max_conversation_turns: int = 20
    token_budget_per_session: int = 50000
    max_context_frames: int = 3

    # Frame strategy
    frame_change_threshold: float = 0.15      # 像素变化>15%才上传
    frame_quality_default: float = 0.6
    frame_quality_low: float = 0.4
    frame_width: int = 320
    frame_height: int = 240

    # WebSocket
    ws_ping_interval: int = 25
    ws_ping_timeout: int = 10

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()