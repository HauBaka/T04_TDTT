from repositories.user_repo import user_repo
from schemas.auth_schema import AuthResponse
from core.exceptions import AppException
from datetime import datetime
import uuid
from repositories.collection_repo import collection_repo
from firebase_admin import auth
import random
import string

class AuthenticationService:
    def __init__(self, token: str) -> None:
        self.token = token

    async def authenticate_user(self) -> AuthResponse:
        # 1. Giải mã và xác thực Token từ Firebase
        decoded_info = self._verify_token()
        uid = decoded_info['uid']
        email = decoded_info.get('email')

        # 2. Kiểm tra user đã tồn tại trong Firestore chưa
        user = await user_repo.get_user(uid)

        if not user:
            # 3. Nếu chưa có, tạo thông tin ngẫu nhiên và tạo User mới
            username = f"user_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
            display_name = f"New user"
            
            user_data = {
                "uid": uid,
                "username": username,
                "display_name": display_name,
                "email": email,
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow()
            }
            await user_repo.create_user(user_data)
            
            # 4. Tạo collection "liked" mặc định cho user mới
            await collection_repo.create_default_liked_collection(uid)
            user = user_data
        else:
            # 5. Nếu đã có, cập nhật thời gian đăng nhập cuối cùng
            await user_repo.update_user(uid, {"last_login": datetime.utcnow()})

        # 6. Trả về thông tin cho người dùng
        return AuthResponse(
            uid=uid,
            username=user.get("username", ""),
            display_name=user.get("display_name", ""),
            email=user.get("email")
        )

    def _verify_token(self) -> dict:
        try:
            # Sử dụng firebase_admin.auth để xác thực toke
            return auth.verify_id_token(self.token)
        except Exception as e:
            raise AppException(f"Xác thực thất bại: {str(e)}", status_code=401)