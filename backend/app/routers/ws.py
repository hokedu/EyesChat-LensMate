"""WebSocket endpoint with privacy mode, interrupt, TTS, and frame management."""
import json
import base64
import asyncio
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..core.config import settings
from ..core.session_manager import SessionManager
from ..core.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()
session_manager = SessionManager(
    max_turns=settings.max_conversation_turns,
    token_budget=settings.token_budget_per_session,
    max_frames=settings.max_context_frames,
)
llm_service = LLMService()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id)
    logger.info("WS connected: %s", session_id)

    try:
        await websocket.send_json({
            "type": "session_start",
            "session_id": session_id,
            "config": {
                "max_turns": settings.max_conversation_turns,
                "token_budget": settings.token_budget_per_session,
                "model": settings.llm_model,
                "max_context_frames": settings.max_context_frames,
            },
        })

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "frame":
                frame_data = data.get("base64", "")
                logger.info("Frame received: %d bytes b64, session: %s", len(frame_data), session_id[:8])
                session_manager.push_frame(session_id, frame_data)
                await websocket.send_json({
                    "type": "frame_ack",
                    "frame_count": len(session.frame_history),
                })

            elif msg_type == "transcript":
                user_text = data.get("text", "")
                if not user_text.strip():
                    continue

                if not session_manager.can_add_turn(session_id):
                    await websocket.send_json({
                        "type": "budget_exhausted",
                        "message": "session budget used up, please start a new conversation.",
                    })
                    continue

                await websocket.send_json({"type": "stream_start"})

                history = session_manager.build_context(session_id)
                latest_frame = None
                if session.frame_history:
                    latest_frame = session.frame_history[-1].base64

                full_text = ""
                async for chunk in llm_service.chat_with_vision(
                    user_text=user_text,
                    frame_base64=latest_frame,
                    scene_summary=session.current_scene_summary,
                    history=history,
                    privacy_mode=session.privacy_mode,
                ):
                    if chunk["type"] == "text":
                        full_text += chunk["content"]
                        await websocket.send_json(chunk)
                    elif chunk["type"] == "meta":
                        session_manager.add_turn(session_id, "user", user_text)
                        meta = json.loads(chunk["content"])
                        session_manager.add_turn(
                            session_id, "assistant", full_text,
                            token_count=meta.get("output_tokens", 0),
                        )
                        await websocket.send_json(chunk)

                await websocket.send_json({"type": "stream_end"})

                # TTS
                if full_text.strip():
                    session.is_ai_speaking = True
                    await websocket.send_json({"type": "tts_start"})
                    audio_bytes = await llm_service.text_to_speech(full_text)
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode()
                        await websocket.send_json({
                            "type": "tts_data",
                            "audio": audio_b64,
                        })
                    session.is_ai_speaking = False
                    await websocket.send_json({"type": "tts_end"})

            elif msg_type == "set_privacy":
                enabled = data.get("enabled", True)
                session_manager.set_privacy_mode(session_id, enabled)
                await websocket.send_json({"type": "privacy_ack", "enabled": enabled})

            elif msg_type == "interrupt":
                session_manager.interrupt_ai(session_id)
                await websocket.send_json({"type": "interrupt_ack"})

            elif msg_type == "get_status":
                await websocket.send_json({
                    "type": "status",
                    "turns": len(session.turns),
                    "token_usage": session.token_usage,
                    "budget_remaining": settings.token_budget_per_session - session.token_usage,
                    "frame_count": len(session.frame_history),
                    "privacy_mode": session.privacy_mode,
                    "scene_summary": session.current_scene_summary,
                    "active_sessions": session_manager.active_session_count,
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", session_id)
    except Exception as e:
        logger.error("WS error: %s: %s", session_id, e)
    finally:
        session_manager.remove_session(session_id)