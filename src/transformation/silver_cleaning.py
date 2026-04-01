import pandas as pd
import numpy as np
import re
import os
import s3fs
import json
from datetime import datetime
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# --- 1. CÁC HÀM CHUẨN HÓA (LOGIC) ---

def clean_price(price_str):
    if pd.isna(price_str): return 0.0
    # Rút trích số đầu tiên tìm thấy (VD: "$120.50" -> 120.50)
    match = re.search(r"(\d+\.?\d*)", str(price_str))
    return float(match.group(1)) if match else 0.0

def extract_currency(price_str):
    if pd.isna(price_str): return "USD"
    price_str = str(price_str).upper()
    if "GBP" in price_str: return "GBP"
    if "EUR" in price_str: return "EUR"
    if "AU" in price_str: return "AUD"
    return "USD"

def infer_purpose(row):
    # Gom tên và dòng sản phẩm lại để tìm từ khóa
    text = (str(row.get('name', '')) + " " + str(row.get('specs.Product Line', ''))).lower()
    
    if any(x in text for x in ['running', 'marathon', 'jogging']): return 'Running'
    if any(x in text for x in ['basketball', 'jordan', 'curry', 'lebron']): return 'Basketball'
    if any(x in text for x in ['soccer', 'football', 'cleat']): return 'Soccer'
    if any(x in text for x in ['hiking', 'trail', 'trekking', 'boot']): return 'Hiking'
    if any(x in text for x in ['training', 'gym', 'crossfit']): return 'Gym & Training'
    if any(x in text for x in ['skate', 'boarding']): return 'Skateboarding'
    
    # Nếu không tìm thấy, lấy thuộc tính có sẵn hoặc để Casual
    original = row.get('specs.Performance/Activity')
    if pd.notna(original) and str(original).strip() != "":
        # Chỉ lấy phần trước dấu phẩy
        return str(original).split(',')[0].strip()
    return 'Casual'

def normalize_material(mat_str):
    if pd.isna(mat_str) or str(mat_str).strip() == "": return "Unknown"
    
    # Lấy vật liệu chính (trước dấu phẩy/gạch chéo)
    m = re.split(r'[,/]', str(mat_str))[0].lower().strip()
    
    if any(x in m for x in ['synthetic', 'faux', 'polyurethane', 'pu']): return 'Synthetic'
    if 'mesh' in m: return 'Mesh'
    if 'canvas' in m: return 'Canvas'
    if 'suede' in m: return 'Suede'
    if any(x in m for x in ['leather', 'nubuck', 'patent', 'skin']): return 'Leather'
    if any(x in m for x in ['textile', 'fabric', 'knit', 'cloth']): return 'Textile'
    if 'rubber' in m: return 'Rubber'
    return 'Unknown'


def main():
    print(f"🚀 BẮT ĐẦU JOB: Silver Cleaning (Powered by Pandas)")
    
    # Cấu hình S3
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME", "sneaker-db")
    
    fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret)
    
    # --- BƯỚC 1: ĐỌC DỮ LIỆU BRONZE TỪ S3 ---
    bronze_path = f"{bucket_name}/bronze/ebay_raw/*/*/*.json"
    print(f"📥 Đang tìm các file JSON tại S3: {bronze_path}")
    
    file_paths = fs.glob(bronze_path)
    if not file_paths:
        print("❌ Không tìm thấy dữ liệu ở tầng Bronze!")
        return
        
    all_data = []
    for path in file_paths:
        # Thêm encoding='utf-8' vào đây nhé 👇
        with fs.open(path, 'r', encoding='utf-8') as f:
            all_data.extend(json.load(f))
            
    # Dùng json_normalize để kéo phẳng (flatten) các cột bên trong 'specs'
    df_raw = pd.json_normalize(all_data)
    count_raw = len(df_raw)
    print(f"📊 [1/4] Số lượng Raw thu thập được: {count_raw}")

    # --- BƯỚC 2: TRANSFORMATION ---
    print("🔄 [2/4] Đang biến đổi dữ liệu...")
    df = pd.DataFrame()
    
    # 1. Tên sản phẩm
    df['product_name'] = df_raw['name']
    
    # 2. Brand (Lấy từ specs, nếu không có thì lấy chữ đầu tiên của Tên)
    df['brand'] = df_raw.get('specs.Brand', pd.Series([np.nan]*len(df_raw)))
    mask_no_brand = df['brand'].isna() | (df['brand'] == '')
    df.loc[mask_no_brand, 'brand'] = df_raw.loc[mask_no_brand, 'name'].apply(
        lambda x: str(x).split()[0] if pd.notna(x) and len(str(x).split()) > 0 else 'Unknown'
    )
    
    # 3. Category (Xóa 's, chuyển Mens -> Men)
    df['category'] = df_raw.get('specs.Department', 'Unisex').fillna('Unisex')
    df['category'] = df['category'].astype(str).str.replace("'s", "", regex=False).str.strip()
    df['category'] = df['category'].replace({'Mens': 'Men', 'Womens': 'Women'})
    
    # 4. Style & Type & Model
    df['style'] = df_raw.get('specs.Style', df_raw.get('specs.Shoe Shaft Style', 'Sneaker')).fillna('Sneaker')
    df['style'] = df['style'].astype(str).str.split(',').str[0].str.strip() # Cắt dấu phẩy
    
    df['type'] = df_raw.get('specs.Type', 'Athletic').fillna('Athletic')
    
    df['model'] = df_raw.get('specs.Model', 'Unknown').fillna('Unknown')
    df['model'] = df['model'].astype(str).str.split(',').str[0].str.strip().str.title() # Cắt và viết hoa
    
    # 5. Purpose (Gọi hàm suy luận)
    df['purpose'] = df_raw.apply(infer_purpose, axis=1)
    
    # 6. Color & Material
    color_col = df_raw.get('specs.Color', df_raw.get('specs.Colour', 'Unknown')).fillna('Unknown')
    df['color'] = color_col.astype(str).str.split(r'[,/]').str[0].str.strip()
    
    mat_col = df_raw.get('specs.Upper Material', df_raw.get('specs.Material', 'Unknown')).fillna('Unknown')
    df['material'] = mat_col.apply(normalize_material)
    
    # 7. Price & URLs
    df['currency'] = df_raw['price'].apply(extract_currency)
    df['price'] = df_raw['price'].apply(clean_price)
    df['image_url'] = df_raw['image_url']
    df['source_url'] = df_raw.get('url', '')
    df['processed_at'] = datetime.now()

    # --- BƯỚC 3: FILTERING & DEDUPLICATION ---
    print("🧹 [3/4] Đang lọc rác và xóa trùng lặp...")
    
    # Lọc rác (Dùng boolean indexing của Pandas)
    mask_clean = (
        (df['image_url'].notna()) &
        (df['price'] > 0) &
        (df['purpose'].str.lower() != 'not specified') &
        (~df['product_name'].str.lower().str.contains('empty box', na=False)) &
        (df['category'] != 'N/A') &
        (df['model'] != 'Unknown') &
        (df['color'] != 'Unknown') &
        (df['material'] != 'Unknown')
    )
    df_filtered = df[mask_clean].copy()
    count_filtered = len(df_filtered)
    
    # Xóa trùng lặp theo tên
    df_final = df_filtered.drop_duplicates(subset=['product_name'], keep='first')
    count_final = len(df_final)
    
    print(f"📉 Đã loại bỏ rác: {count_raw - count_filtered} dòng.")
    print(f"📉 Đã xóa trùng lặp: {count_filtered - count_final} dòng.")
    print(f"✅ TỔNG SỐ SẢN PHẨM SẠCH CUỐI CÙNG: {count_final}")

    # --- BƯỚC 4: GHI DỮ LIỆU XUỐNG S3 (SILVER) ---
    output_path = f"s3://{bucket_name}/silver/products/products_clean.parquet"
    print(f"💾 [4/4] Đang ghi xuống Silver tại: {output_path}")
    
    # Ghi định dạng Parquet trực tiếp lên S3
    df_final.to_parquet(
        output_path, 
        index=False, 
        storage_options={"key": aws_key, "secret": aws_secret}
    )
    
    print("🎉 JOB HOÀN TẤT THÀNH CÔNG!")

if __name__ == "__main__":
    main()