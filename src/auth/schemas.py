from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None

class UserResponse(BaseModel):
    user_id: int
    username: str
    
    class Config:
        from_attributes = True

class InteractionCreate(BaseModel):
    product_id: str
    action_type: str