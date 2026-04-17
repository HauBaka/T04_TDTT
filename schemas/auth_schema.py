from pydantic import BaseModel, Field, model_validator

class AuthRequest(BaseModel):
    token: str

class AuthResponse(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str | None = None
    #...