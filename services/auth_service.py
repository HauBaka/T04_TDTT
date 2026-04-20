from repositories.user_repo import user_repo
from schemas.auth_schema import AuthResponse
from schemas.response_schema import ResponseSchema
from core.exceptions import AppException
from datetime import datetime, timezone
import uuid
from repositories.collection_repo import collection_repo
from schemas.collection_schema import CollectionCreateRequest, CollectionVisibility
from firebase_admin import auth
import random
import string

class AuthenticationService:
    def __init__(self, token: str) -> None:
        self.token = token

    async def authenticate_user(self) -> ResponseSchema[AuthResponse]:
        # 1. Giải mã và xác thực Token từ Firebase
        decoded_info = self._verify_token()
        uid = decoded_info['uid']
        email = decoded_info.get('email')

        try:
            # 2. Kiểm tra user đã tồn tại chưa
            user = await user_repo.get_user(uid)

            if not user:
                # --- TRƯỜNG HỢP TẠO MỚI ---
                
                # 3. Sinh username duy nhất (có check trùng)
                username = await self._generate_unique_username()
                
                # 4. Tạo collection "Liked" mặc định và lấy ID
                liked_req = CollectionCreateRequest(
                    name="Liked", 
                    description="Your liked accomodation", 
                    visibility=CollectionVisibility.PRIVATE
                )
                new_collection = await collection_repo.create_collection(uid, liked_req)
                liked_collection_id = new_collection.get("id")
                
                if not liked_collection_id:
                    raise AppException(status_code=500, message="Could not initialize user data")

                # 5. Lưu User mới với đầy đủ thông tin
                user_data = {
                    "uid": uid,
                    "username": username,
                    "display_name": "New user",
                    "email": email,
                    "liked_collection": liked_collection_id, # Lưu ID vào user theo yêu cầu
                    "created_at": datetime.now(timezone.utc),
                    "last_login": datetime.now(timezone.utc)
                }
                user = await user_repo.create_user(user_data)
            else:
                # --- TRƯỜNG HỢP ĐÃ TỒN TẠI ---
                
                # 6. Cập nhật last_login
                update_data = {"last_login": datetime.now(timezone.utc)}
                user = await user_repo.update_user(uid, update_data)

            # 7. Trả về ResponseSchema bọc AuthResponse
            return ResponseSchema(
                status_code=200,
                message="Success",
                data=AuthResponse(
                    uid=uid,
                    username=user.get("username", ""),
                    display_name=user.get("display_name", ""),
                    email=user.get("email")
                )
            )

        except Exception as e:
            # 8. ROLLBACK: Nếu là user mới mà lỗi thì xóa trên Firebase
            # Kiểm tra nếu user chưa tồn tại trong DB trước khi lỗi xảy ra
            if not await user_repo.get_user(uid):
                try:
                    auth.delete_user(uid)
                except:
                    pass
            
            if isinstance(e, AppException):
                raise e
            raise AppException(status_code=500, message=f"Account creation failed: {str(e)}")


    async def _generate_unique_username(self) -> str:
        """Sinh username ngẫu nhiên và kiểm tra trùng lặp."""
        while True:
            new_username = f"user_{uuid.uuid4().hex[:8]}"
            # Truy vấn vào DB xem có ai dùng tên này chưa
            existing = await user_repo.get_user_by_username(new_username)
            if not existing:
                return new_username

    def _verify_token(self) -> dict:
        try:
            # Sử dụng firebase_admin.auth để xác thực toke
            return auth.verify_id_token(self.token)
        except Exception as e:
            raise AppException(f"Xác thực thất bại: {str(e)}", status_code=401)