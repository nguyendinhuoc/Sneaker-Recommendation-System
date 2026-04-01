import boto3
import os
from datetime import datetime
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

# 1. Nạp file .env
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# Sửa lại thành BUCKET_NAME cho khớp với file .env cũ
BUCKET_NAME = os.getenv("S3_BUCKET_NAME") 

# Danh sách các file cần upload (File nguồn -> Folder đích trên S3)
UPLOAD_PLAN = [
    ("data/raw/users.csv", "bronze/users"),
    ("data/raw/user_interactions.csv", "bronze/interactions")
]

def upload_to_s3():
    # Kiểm tra biến môi trường
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not BUCKET_NAME:
        print("❌ Lỗi: Thiếu thông tin trong file .env")
        return

    print(f"🔌 Đang kết nối tới AWS S3 (Bucket: {BUCKET_NAME})...")

    s3_client = boto3.client('s3',
                             aws_access_key_id=AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    try:
        # Kiểm tra Bucket
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"✅ Bucket '{BUCKET_NAME}' đã sẵn sàng.\n")

        # Lấy thời gian chung cho cả lô upload này
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp_str = datetime.now().strftime("%H-%M-%S")

        # Vòng lặp upload từng file
        for local_path, s3_folder in UPLOAD_PLAN:
            if os.path.exists(local_path):
                # Tách tên file và đuôi file (ví dụ: users .csv)
                filename = os.path.basename(local_path)
                name_part, ext_part = os.path.splitext(filename)
                
                # Tạo tên file mới có timestamp để tránh ghi đè
                # Ví dụ: users_10-30-00.csv
                new_filename = f"{name_part}_{timestamp_str}{ext_part}"
                
                # Đường dẫn đầy đủ trên S3
                s3_object_name = f"{s3_folder}/{today}/{new_filename}"

                print(f"⬆️  Đang upload: {filename}")
                print(f"    -> S3 Path: {s3_object_name}")
                
                s3_client.upload_file(local_path, BUCKET_NAME, s3_object_name)
                print("    ✅ Thành công!")
            else:
                print(f"⚠️  Bỏ qua: Không tìm thấy file '{local_path}'")

        print("\n🎉 TẤT CẢ FILE ĐÃ ĐƯỢC UPLOAD LÊN DATA LAKE!")

    except NoCredentialsError:
        print("❌ Lỗi: Sai Credentials.")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    upload_to_s3()