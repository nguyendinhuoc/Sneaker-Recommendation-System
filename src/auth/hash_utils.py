from passlib.context import CryptContext

# Khởi tạo context với thuật toán bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hàm băm mật khẩu"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Hàm kiểm tra mật khẩu nhập vào có khớp với bản đã băm không"""
    return pwd_context.verify(plain_password, hashed_password)