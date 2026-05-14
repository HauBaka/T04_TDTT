from repositories.user_repo import user_repo
from schemas.auth_schema import AuthResponse
from schemas.response_schema import ResponseSchema
from core.exceptions import AppException, InternalServerError, NotFoundError
from datetime import datetime, timezone
import uuid
from repositories.collection_repo import collection_repo
from schemas.collection_schema import CollectionCreateRequest, CollectionVisibility
from services.conversation_service import conversation_service
from schemas.user_schema import UserCreateRequest

class AuthenticationService:
    def __init__(self, uid: str, email: str) -> None:
        self.uid = uid
        self.email = email

    async def authenticate_user(self) -> ResponseSchema[AuthResponse]:

        now = datetime.now(timezone.utc)
        try:
            # Kiểm tra user đã tồn tại chưa
            user = await user_repo.get_user(self.uid)
            # --- TRƯỜNG HỢP ĐÃ TỒN TẠI ---
            
            # Cập nhật last_login
            update_data = {"last_login": now}
            await user_repo.batch_update_users([self.uid], [update_data])

        except NotFoundError:
            # --- TRƯỜNG HỢP TẠO MỚI ---
            
            # Sinh username duy nhất (có check trùng)
            username = await self._generate_unique_username()
            
            # Tạo collection "Liked" mặc định và lấy ID
            liked_req = CollectionCreateRequest(
                name="Liked", 
                description="Your liked accommodations", 
                tags = [],
                visibility=CollectionVisibility.PRIVATE,
                thumbnail_url=None
            )
            liked_collection = await collection_repo.create_collection(self.uid, liked_req)

            # Tạo default chatbot conversation
            chatbot_conversation = await conversation_service.get_or_create_default_chatbot_conversation(self.uid)
            if not chatbot_conversation.data:
                raise InternalServerError(message="Failed to create default chatbot conversation")

            # Lưu User mới với đầy đủ thông tin
            user_request = UserCreateRequest(
                uid = self.uid,
                username = username,
                username_lower = username.lower(),
                email=self.email,
                phone_number=None,

                display_name=self._generate_display_name(),
                avatar_url=None,
                bio=None,
                chatbot_conversation=chatbot_conversation.data.id,

                liked_collection=liked_collection.id,
                created_at=now,
                last_login=now,
                last_updated=None
            )

            user = await user_repo.create_user(user_request)

        # Trả về ResponseSchema bọc AuthResponse
        return ResponseSchema(
            status_code=200,
            message="Success",
            data=AuthResponse(
                uid=self.uid,
                username=user.username,
                display_name=user.display_name,
                email=self.email,
                avatar_url=user.avatar_url
            )
        )

    async def _generate_unique_username(self) -> str:
        """Sinh username ngẫu nhiên và kiểm tra trùng lặp."""
        for _ in range(5):  # Thử tối đa 5 lần để tránh vòng lặp vô hạn
            new_username = f"user_{uuid.uuid4().hex[:8]}"
            # Truy vấn vào DB xem có ai dùng tên này chưa
            try:
                await user_repo.get_user_by_username(new_username)
            except NotFoundError:
                return new_username
        raise InternalServerError(message="Failed to generate unique username")


    def _generate_display_name(self) -> str:
        return f"Booking4U {uuid.uuid4().hex[:6]}"
