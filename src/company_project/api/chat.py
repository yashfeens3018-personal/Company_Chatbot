from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from ..AI_Chat.chat import app as chatbot 
from ..auth.security import get_user

router = APIRouter(prefix="/chat", tags=["chat"])

conversations: dict[tuple[str, str], list] = {}
MAX_HISTORY = 20


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: Annotated[dict, Depends(get_user)]):
    conversation_id = request.conversation_id or str(uuid4())
    key = (current_user["email"], conversation_id)
    history = list(conversations.get(key, []))[-MAX_HISTORY:]
    history.append(HumanMessage(content=request.message))
    try:
        result = chatbot.invoke({"messages": history, "employee_email": current_user["email"]})
    except Exception:
        raise HTTPException(status_code=502, detail="The assistant could not answer right now. Please try again.")
    conversations[key] = result["messages"]
    return ChatResponse(conversation_id=conversation_id, answer=result["messages"][-1].content)