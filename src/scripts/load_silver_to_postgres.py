import pandas as pd
from sqlalchemy import create_engine
import os
import s3fs
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

def load_silver_products():
    bucket_name = "sneaker-db"
    folder_path = "silver/products"
    
    print(f"--- 🔄 Đang kết nối S3: {bucket_name}/{folder_path} ---")
    try:
        # 1. Khởi tạo filesystem
        fs = s3fs.S3FileSystem(
            key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        # 2. Liệt kê tất cả các file parquet trong folder
        files = fs.glob(f"{bucket_name}/{folder_path}/*.parquet")
        if not files:
            print("❌ Không tìm thấy file .parquet nào trong folder!")
            return

        print(f"--- 📂 Tìm thấy {len(files)} file. Đang đọc dữ liệu... ---")
        
        # 3. Đọc tất cả các file và gộp lại 
        all_dfs = []
        for file in files:
            # Đọc từng file bằng pyarrow để tránh lỗi Float truncated
            with fs.open(file) as f:
                table = pq.read_table(f)
                all_dfs.append(table.to_pandas())
        
        # Gộp tất cả các bảng lại thành một DataFrame duy nhất
        df = pd.concat(all_dfs, ignore_index=True)
        
        print(f"--- 📥 Đã tải {len(df)} dòng. Đang chuẩn hóa... ---")
        
        # 1. Tự tạo product_id nếu không có (Tạo ID bắt đầu từ 1)
        if 'product_id' not in df.columns:
            print("⚠️ Không tìm thấy product_id, đang tự động tạo ID từ Index bắt đầu bằng 1...")
            df['product_id'] = (df.index + 1).astype(str)

        # 2. Transform dữ liệu (Làm sạch giá trị)
        # Ép kiểu price về float (chấp nhận 75.99)
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0).astype(float)
        
        # 3. Mapping sang cấu trúc bảng Postgres (HỨNG TOÀN BỘ CHI TIẾT)
        # Khai báo các cột có giá trị kinh doanh từ S3 mà ta muốn giữ lại
        cols_from_s3 = [
            'product_id', 'product_name', 'brand', 'category', 'style', 
            'type', 'model', 'purpose', 'color', 'material', 'currency', 
            'price', 'image_url', 'source_url'
        ]
        
        # Chỉ lấy những cột thực sự tồn tại trong DataFrame để tránh lỗi KeyError
        existing_cols = [col for col in cols_from_s3 if col in df.columns]
        df_display = df[existing_cols].copy()
        
        # Đổi tên 'product_name' thành 'name' cho khớp hoàn toàn với Backend hiện tại
        if 'product_name' in df_display.columns:
            df_display.rename(columns={'product_name': 'name'}, inplace=True)

        # 4. Load vào Postgres
        # 4. Load vào Postgres trên MÂY
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url)
        
        print(f"--- 📤 Đang nạp {len(df_display)} sản phẩm vào Cloud Postgres... ---")
        df_display.to_sql('products', engine, if_exists='replace', index=False, method='multi')
        
        print(f"✅ THÀNH CÔNG! Bảng 'products' đã được cập nhật với đầy đủ thông số kỹ thuật.")
        
    except Exception as e:
        print(f"❌ Lỗi thực thi: {str(e)}")

if __name__ == "__main__":
    load_silver_products()