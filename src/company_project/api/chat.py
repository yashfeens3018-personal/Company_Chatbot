"""
Drop-in replacement for src/company_project/api/chat.py (save it under that name).

What it adds over the original:
  1. One message at a time PER CONVERSATION (a lock), so two requests for the same
     conversation can't overwrite each other's history (the "lost update" race).
  2. A cap on how many graph runs happen at the same time across ALL users, so a burst
     of users can't exhaust the Gemini rate limit or the DB connection pool.
  3. A bounded in-memory store (least-recently-used conversations are dropped), so
     memory can't grow forever.
  4. Input size limits and error logging (the original swallowed the real error).

Still true: this state lives in ONE process. Run a single uvicorn worker until the
conversation store moves to a database/Redis (see the notes in the chat).
"""
import logging
import threading
from collections import OrderedDict
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from ..AI_Chat.chat import app as chatbot
from ..AI_Chat.cache import purge_stale
from ..auth.security import get_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

MAX_HISTORY = 20                # messages sent to the graph per turn
MAX_CONVERSATIONS = 1000        # in-memory conversations kept (least recently used dropped)
CONVERSATION_LOCK_WAIT = 30     # seconds a 2nd message waits for the 1st one in the same conversation
MAX_CONCURRENT_RUNS = 8         # graph runs allowed at once, all users together
SLOT_WAIT = 30                  # seconds to wait for a free run slot before answering 503

_graph_slots = threading.BoundedSemaphore(MAX_CONCURRENT_RUNS)


class Conversation:
    __slots__ = ("lock", "messages")

    def __init__(self):
        self.lock = threading.Lock()
        self.messages: list = []


class ConversationStore:
    """Thread-safe, in-memory. Keep these two methods if you later back it with a database."""

    def __init__(self):
        self._items: OrderedDict[tuple[str, str], Conversation] = OrderedDict()
        self._guard = threading.Lock()   # protects the dict itself, held only for an instant

    def get_or_create(self, key: tuple[str, str]) -> Conversation:
        with self._guard:
            conv = self._items.get(key)
            if conv is None:
                conv = self._items[key] = Conversation()
            self._items.move_to_end(key)
            self._evict_if_needed(keep=key)
            return conv

    def _evict_if_needed(self, keep: tuple[str, str]) -> None:
        # caller holds self._guard. Drop least-recently-used conversations nobody is using.
        while len(self._items) > MAX_CONVERSATIONS:
            for old_key, old in self._items.items():
                if old_key != keep and not old.lock.locked():
                    del self._items[old_key]
                    break
            else:
                return   # everything left is in use


store = ConversationStore()


@router.on_event("startup")
def purge_stale_chat_cache() -> None:
    purge_stale()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str


# Plain `def` on purpose: FastAPI runs it in a worker thread, so the blocking
# chatbot.invoke() below doesn't freeze the server. Do NOT turn this into `async def`
# unless you also switch to `await chatbot.ainvoke(...)`.
@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: Annotated[dict, Depends(get_user)]):
    conversation_id = request.conversation_id or str(uuid4())
    key = (current_user["email"], conversation_id)   # the user is part of the key: no cross-user access
    conv = store.get_or_create(key)

    # 1) one message at a time per conversation
    if not conv.lock.acquire(timeout=CONVERSATION_LOCK_WAIT):
        raise HTTPException(status_code=409, detail="Your previous message in this conversation is still being answered. Please wait a moment.")
    try:
        # 2) global cap on simultaneous graph runs
        if not _graph_slots.acquire(timeout=SLOT_WAIT):
            raise HTTPException(status_code=503, detail="The assistant is busy right now. Please try again in a moment.")
        try:
            history = conv.messages[-MAX_HISTORY:] + [HumanMessage(content=request.message)]
            result = chatbot.invoke({"messages": history, "user": current_user})
        except Exception:
            logger.exception("Chat failed (conversation %s)", conversation_id)
            raise HTTPException(status_code=502, detail="The assistant could not answer right now. Please try again.")
        finally:
            _graph_slots.release()
        conv.messages = result["messages"]   # only saved on success, and only while we hold the lock
    finally:
        conv.lock.release()

    return ChatResponse(conversation_id=conversation_id, answer=result["messages"][-1].content)