import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    # Lấy thông tin từ file .env của bạn
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database=os.getenv("DB_NAME", "sneaker_db"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password")
    )
    cur = conn.cursor()

    # 1. Tạo bảng Users (Dành cho Authentication)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            gender VARCHAR(20),
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Tạo bảng Interactions (Để React bắn dữ liệu về)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            product_id INTEGER NOT NULL,
            interaction_type VARCHAR(20), -- view, click, buy
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Đã khởi tạo các bảng Users và Interactions thành công!")

if __name__ == "__main__":
    init_db()