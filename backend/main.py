from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.chatbot.intent_matcher import IntentMatcher

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Asis Chatbot API", version="1.0.0")
matcher = IntentMatcher()


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    """Kullanıcı mesajını alır, niyet eşleştirmesi yapıp yanıt döner."""
    return matcher.match(request.message)


# Statik site en sonda mount edilir ki /api rotaları öncelikli olsun
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
