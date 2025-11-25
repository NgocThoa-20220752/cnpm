from pydantic import BaseModel
from app.enum import RoleEnum


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str
    full_name: str
    role: RoleEnum


class MessageResponse(BaseModel):
    message: str