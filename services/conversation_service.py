
from datetime import datetime

from repositories import conversation_repo
from schemas.conversation_schema import ConversationResponse, ConversationCreateRequest, ConversationUpdateRequest, AddMembersRequest, SendMessageRequest
from schemas.response_schema import ResponseSchema


class ConversationService:
    def __init__(self):
        self.conversation_repository = conversation_repo

    async def create_conversation(self, owner_uid: str, conversation_data: dict) -> ResponseSchema[ConversationResponse]:
        """Tạo một conversation mới."""
        return ResponseSchema(data=ConversationResponse(**conversation_data))
    
    async def get_conversation(self, conversation_id: str, requester_uid: str | None) -> ResponseSchema[ConversationResponse]:
        """Lấy thông tin một conversation theo ID."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name="conversation_name", 
                description="conversation_description", 
                thumbnail_url=None, 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )
    
    async def update_conversation(self, conversation_id: str, requester_uid: str, update_data: dict) -> ResponseSchema[ConversationResponse]:
        """Cập nhật thông tin một conversation."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name=update_data.get("name", "conversation_name"), 
                description=update_data.get("description", "conversation_description"), 
                thumbnail_url=update_data.get("thumbnail_url", None), 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )
    
    async def delete_conversation(self, conversation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một conversation."""
        return ResponseSchema(data=True)
    
    async def add_members_to_conversation(self, conversation_id: str, requester_uid: str, request: AddMembersRequest) -> ResponseSchema[ConversationResponse]:
        """Thêm nhiều thành viên vào một conversation."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name="conversation_name", 
                description="conversation_description", 
                thumbnail_url=None, 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )
    
    async def remove_members_from_conversation(self, conversation_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[ConversationResponse]:
        """Xóa nhiều thành viên khỏi một conversation."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name="conversation_name", 
                description="conversation_description", 
                thumbnail_url=None, 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )
    
    async def send_message_to_conversation(self, conversation_id: str, requester_uid: str, message_data: SendMessageRequest) -> ResponseSchema[ConversationResponse]:
        """Gửi một tin nhắn mới vào một conversation."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name="conversation_name", 
                description="conversation_description", 
                thumbnail_url=None, 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )

    async def delete_message_from_conversation(self, conversation_id: str, message_id: str, requester_uid: str) -> ResponseSchema[ConversationResponse]:
        """Xóa một tin nhắn khỏi một conversation."""
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid="owner_uid", 
                name="conversation_name", 
                description="conversation_description", 
                thumbnail_url=None, 
                created_at=datetime.now(), 
                updated_at=datetime.now(), 
                members=[])
            )
    


conversation_service = ConversationService()