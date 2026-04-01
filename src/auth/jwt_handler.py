import time
from typing import Dict
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Các tham số cấu hình (Nên để trong file .env)
JWT_SECRET = os.getenv("JWT_SECRET", "my_super_secret_key_123")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def token_response(token: str):
    return {
        "access_token": token
    }

def signJWT(user_id: int) -> Dict[str, str]:
    # Tạo payload chứa ID người dùng và thời gian hết hạn (ví dụ 1 tiếng)
    payload = {
        "user_id": user_id,
        "expires": time.time() + 3600
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except:
        return {}