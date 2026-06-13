"""Session manager with scene summary, frame history, and privacy mode."""
import time
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str
    text: str
    token_count: int = 0
    timestamp: float = 0.0


@dataclass
class FrameRecord:
    base64: str
    timestamp: float
    scene_summary: str = ""


@dataclass
class SessionState:
    session_id: str
    created_at: float = 0.0
    turns: list[ConversationTurn] = field(default_factory=list)
    token_usage: int = 0
    frame_history: list[FrameRecord] = field(default_factory=list)
    current_scene_summary: str = ""
    privacy_mode: bool = False
    is_ai_speaking: bool = False
    interrupted: bool = False
    user_wants_adjust: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    def __init__(self, max_turns: int = 20, token_budget: int = 50000, max_frames: int = 3):
        self._sessions: dict[str, SessionState] = {}
        self._max_turns = max_turns
        self._token_budget = token_budget
        self._max_frames = max_frames

    def create_session(self, session_id: str) -> SessionState:
        state = SessionState(session_id=session_id, created_at=time.time())
        self._sessions[session_id] = state
        logger.info("Session created: %s", session_id)
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        logger.info("Session removed: %s", session_id)

    def can_add_turn(self, session_id: str) -> bool:
        state = self._sessions.get(session_id)
        if not state:
            return False
        return len(state.turns) < self._max_turns and state.token_usage < self._token_budget

    def add_turn(self, session_id: str, role: str, text: str, token_count: int = 0):
        state = self._sessions.get(session_id)
        if not state:
            return
        state.turns.append(ConversationTurn(
            role=role, text=text,
            token_count=token_count, timestamp=time.time(),
        ))
        state.token_usage += token_count

    def push_frame(self, session_id: str, frame_base64: str):
        """Push a frame into history; keep only last N frames."""
        state = self._sessions.get(session_id)
        if not state:
            return
        state.frame_history.append(FrameRecord(
            base64=frame_base64, timestamp=time.time()
        ))
        if len(state.frame_history) > self._max_frames:
            state.frame_history.pop(0)

    def set_scene_summary(self, session_id: str, summary: str):
        state = self._sessions.get(session_id)
        if state:
            state.current_scene_summary = summary
            if state.frame_history:
                state.frame_history[-1].scene_summary = summary

    def set_privacy_mode(self, session_id: str, enabled: bool):
        state = self._sessions.get(session_id)
        if state:
            state.privacy_mode = enabled
            logger.info("Privacy mode %s for %s", "ON" if enabled else "OFF", session_id)

    def interrupt_ai(self, session_id: str):
        state = self._sessions.get(session_id)
        if state:
            state.interrupted = True
            state.is_ai_speaking = False

    def is_budget_exhausted(self, session_id: str) -> bool:
        state = self._sessions.get(session_id)
        if not state:
            return True
        return state.token_usage >= self._token_budget

    def build_context(self, session_id: str) -> list[dict]:
        """Build messages context for LLM."""
        state = self._sessions.get(session_id)
        if not state:
            return []
        context = []
        for turn in state.turns:
            context.append({"role": turn.role, "content": turn.text})
        return context

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)