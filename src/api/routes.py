from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.domain.agent import (
    resolve_user_id,
    get_user_threads,
    get_thread_messages,
    invoke_chat,
)

router = APIRouter()

class AuthRequest(BaseModel):
    api_key: str

class ChatMessageRequest(AuthRequest):
    thread_id: str
    message: str
    model: str = "openai/gpt-oss-20b"

@router.post("/login-and-threads")
def login_and_fetch_threads(req: AuthRequest):
    if not req.api_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Valid Groq API key (starting with gsk_) is required.")
    try:
        user_id = resolve_user_id(req.api_key)
        threads = get_user_threads(user_id)
        return {"user_id": user_id, "threads": threads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/threads/{thread_id}/history")
def fetch_history(thread_id: str, req: AuthRequest):
    if not req.api_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Valid Groq API key (starting with gsk_) is required.")
    try:
        messages = get_thread_messages(thread_id, req.api_key)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
def chat(req: ChatMessageRequest):
    if not req.api_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Valid Groq API key (starting with gsk_) is required.")
    try:
        user_id = resolve_user_id(req.api_key)
        reply = invoke_chat(user_id, req.thread_id, req.message, req.api_key, req.model)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))