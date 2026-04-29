from fastapi import APIRouter, Depends
from schemas.conversation_schema import AddMembersRequest, ConversationCreateRequest, ConversationResponse, ConversationUpdateRequest, SendMessageRequest
from schemas.response_schema import ResponseSchema
from services.conversation_service import conversation_service
from core.dependencies import get_current_user

conversation_router = APIRouter()
# --- QUẢN LÝ HỘI THOẠI (CONVERSATIONS) ---
@conversation_router.post("/conversations", response_model=ResponseSchema[ConversationResponse])
async def create_conversation(conversation_request: ConversationCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một conversation mới cho người dùng đã xác thực."""
    return await conversation_service.create_conversation(requester.get("uid"), conversation_request.model_dump(exclude_none=True))

@conversation_router.get("/conversations/{conversation_id}", response_model=ResponseSchema[ConversationResponse])
async def get_conversation(conversation_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy thông tin của một conversation."""
    return await conversation_service.get_conversation(conversation_id, requester.get("uid") if requester else None)

@conversation_router.patch("/conversations/{conversation_id}", response_model=ResponseSchema[ConversationResponse])
async def update_conversation(conversation_id: str, conversation_request: ConversationUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật thông tin của một conversation."""
    return await conversation_service.update_conversation(conversation_id, requester.get("uid"), conversation_request.model_dump(exclude_none=True))

@conversation_router.delete("/conversations/{conversation_id}", response_model=ResponseSchema[bool])
async def delete_conversation(conversation_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một conversation."""
    return await conversation_service.delete_conversation(conversation_id, requester.get("uid"))

# --- QUẢN LÝ THÀNH VIÊN (MEMBERS) ---
@conversation_router.post("/conversations/{conversation_id}/members", response_model=ResponseSchema[ConversationResponse])
async def add_members_to_conversation(conversation_id: str, member: AddMembersRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều thành viên vào một conversation."""
    return await conversation_service.add_members_to_conversation(conversation_id, requester.get("uid"), member)

@conversation_router.delete("/conversations/{conversation_id}/members", response_model=ResponseSchema[ConversationResponse])
async def remove_members_from_conversation(conversation_id: str, target_uid: str, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều thành viên khỏi một conversation."""
    return await conversation_service.remove_members_from_conversation(conversation_id, requester.get("uid"), [target_uid])

# --- QUẢN LÝ TIN NHẮN (MESSAGES) & UNREAD STATUS ---
@conversation_router.post("/conversations/{conversation_id}/messages", response_model=ResponseSchema[ConversationResponse])
async def send_message_to_conversation(conversation_id: str, message_request: SendMessageRequest, requester=Depends(get_current_user(optional=False))):
    """Gửi một tin nhắn mới vào một conversation."""
    return await conversation_service.send_message_to_conversation(conversation_id, requester.get("uid"), message_request)

@conversation_router.delete("/conversations/{conversation_id}/messages/{message_id}", response_model=ResponseSchema[ConversationResponse])
async def delete_message_from_conversation(conversation_id: str, message_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một tin nhắn cụ thể khỏi một conversation."""
    return await conversation_service.delete_message_from_conversation(conversation_id, message_id, requester.get("uid"))

# Hàm này thêm dô để lỡ bên FE muốn dùng để đánh dấu đã đọc để reset unread nhó sếp :<
@conversation_router.patch("/conversations/{conversation_id}/read", response_model=ResponseSchema[bool])
async def mark_as_read(conversation_id: str, requester=Depends(get_current_user(optional=False))):
    """Endpoint để FE chủ động báo rằng user đã đọc tin nhắn."""
    return await conversation_service.mark_conversation_as_read(conversation_id, requester.get("uid"))