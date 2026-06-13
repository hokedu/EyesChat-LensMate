"""EyesChat-LensMate config."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
import dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    dotenv.load_dotenv(_env_path, override=True)


class Settings(BaseSettings):
    app_name: str = "EyesChat-LensMate"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o"
    whisper_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Session control (relaxed for dev/demo)
    max_conversation_turns: int = 50
    token_budget_per_session: int = 500000
    max_context_frames: int = 3

    # Frame strategy
    frame_change_threshold: float = 0.15
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

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()