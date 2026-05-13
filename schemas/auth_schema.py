from pydantic import BaseModel


class AuthResponse(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    # ...
