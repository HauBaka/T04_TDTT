from fastapi import Header
from firebase_admin import auth
from firebase_admin.auth import (
    InvalidIdTokenError,
    ExpiredIdTokenError,
    RevokedIdTokenError,
    CertificateFetchError
)
from core.exceptions import UnauthorizedError

def get_current_user(optional: bool = False):
    async def dependency(authorization: str | None = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            if optional:
                return None
            raise UnauthorizedError("Missing token")

        token = authorization.split(" ")[1]

        try:
            return auth.verify_id_token(token)

        except (InvalidIdTokenError,
                ExpiredIdTokenError,
                RevokedIdTokenError,
                CertificateFetchError):
            if optional:
                return None
            raise UnauthorizedError("Invalid or expired token")

        except Exception:
            if optional:
                return None
            raise UnauthorizedError("Token verification failed")

    return dependency