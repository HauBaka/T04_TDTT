from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.chatbot_schema import ChatAskRequest, ChatAskResponse
from schemas.response_schema import ResponseSchema
from services.chatbot_service import chatbot_service


chatbot_router = APIRouter()


@chatbot_router.post("/chatbot/ask", response_model=ResponseSchema[ChatAskResponse])
async def ask_chatbot(
    payload: ChatAskRequest,
    requester=Depends(get_current_user(optional=True)),
):
    requester_uid = requester.get("uid") if requester else None
    return await chatbot_service.ask(requester_uid, payload)
