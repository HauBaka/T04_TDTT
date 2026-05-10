from repositories.user_repo import user_repo
from schemas.auth_schema import AuthResponse
from schemas.response_schema import ResponseSchema
from core.exceptions import AppException
from datetime import datetime, timezone
import uuid
from repositories.collection_repo import collection_repo
from schemas.collection_schema import CollectionCreateRequest, CollectionVisibility
from firebase_admin import auth

class AuthenticationService:
    def __init__(self, uid: str, email: str) -> None:
        self.uid = uid
        self.email = email

    async def authenticate_user(self) -> ResponseSchema[AuthResponse]:
        # 1. Giải mã và xác thực Token từ Firebase

        try:
            # 2. Kiểm tra user đã tồn tại chưa
            user = await user_repo.get_user(self.uid)

            if not user:
                # --- TRƯỜNG HỢP TẠO MỚI ---
                
                # 3. Sinh username duy nhất (có check trùng)
                username = await self._generate_unique_username()
                
                # 4. Tạo collection "Liked" mặc định và lấy ID
                liked_req = CollectionCreateRequest(
                    name="Liked", 
                    description="Your liked accommodations", 
                    tags = [],
                    visibility=CollectionVisibility.PRIVATE,
                    thumbnail_url=None
                )
                new_collection = await collection_repo.create_collection(self.uid, liked_req.model_dump())

                if not new_collection or not new_collection.get("id"):
                    raise AppException(status_code=500, message="Failed to initialize user data")
                
                liked_collection_id = new_collection.get("id")

                # 5. Lưu User mới với đầy đủ thông tin
                user_data = {
                    "uid": self.uid,
                    "username": username,
                    "username_lower": username.lower(),  # Dùng để tìm kiếm không phân biệt hoa thường
                    "display_name": self._generate_display_name(),
                    "email": self.email,
                    "liked_collection": liked_collection_id, # Lưu ID vào user theo yêu cầu
                    "created_at": datetime.now(timezone.utc),
                    "last_login": datetime.now(timezone.utc)
                }

                await user_repo.create_user(user_data)
                user = user_data  # Dùng dữ liệu vừa tạo để trả về response

            else:
                # --- TRƯỜNG HỢP ĐÃ TỒN TẠI ---
                
                # 6. Cập nhật last_login
                update_data = {"last_login": datetime.now(timezone.utc)}
                await user_repo.update_user(self.uid, update_data)

            # 7. Trả về ResponseSchema bọc AuthResponse
            return ResponseSchema(
                status_code=200,
                message="Success",
                data=AuthResponse(
                    uid=self.uid,
                    username=user.get("username", ""),
                    display_name=user.get("display_name", ""),
                    email=self.email
                )
            )

        except Exception as e:
            # Không rollback nữa
            if isinstance(e, AppException):
                raise e
            raise AppException(status_code=500, message="Authentication initialization failed")


    async def _generate_unique_username(self) -> str:
        """Sinh username ngẫu nhiên và kiểm tra trùng lặp."""
        for _ in range(5):  # Thử tối đa 5 lần để tránh vòng lặp vô hạn
            new_username = f"user_{uuid.uuid4().hex[:8]}"
            # Truy vấn vào DB xem có ai dùng tên này chưa
            existing = await user_repo.get_user_by_username(new_username)
            if not existing:
                return new_username
        raise AppException(status_code=500, message="Failed to generate unique username")


    def _generate_display_name(self) -> str:
        return f"Booking4U {uuid.uuid4().hex[:6]}"
