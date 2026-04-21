from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import decodeJWT


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

        if credentials.scheme != "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme.")

        payload = decodeJWT(credentials.credentials)
        if not payload or "user_id" not in payload:
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")

        return credentials.credentials