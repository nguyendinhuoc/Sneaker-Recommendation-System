from datetime import datetime, timedelta, timezone
import jwt

SECRET_KEY = "YOUR_SECRET_KEY"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def signJWT(user_id: int):
    payload = {
        "user_id": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


def decodeJWT(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token
    except Exception as e:
        print("DECODE JWT ERROR:", e)
        return None