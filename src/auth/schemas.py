from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    age: Optional[int] = 20
    gender: Optional[str] = "Nam"

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username không được để trống")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: Optional[str]) -> str:
        allowed = {"Nam", "Nữ", "Khác"}
        value = (value or "Nam").strip()
        if value not in allowed:
            raise ValueError("Giới tính không hợp lệ")
        return value


class UserResponse(BaseModel):
    user_id: int
    username: str

    class Config:
        from_attributes = True