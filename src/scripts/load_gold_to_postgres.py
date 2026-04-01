import pandas as pd
import s3fs
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def load_gold_data():
    fs = s3fs.S3FileSystem(key=os.getenv("AWS_ACCESS_KEY_ID"), secret=os.getenv("AWS_SECRET_ACCESS_KEY"))
    engine = create_engine(f"postgresql://admin:admin@localhost:5433/sneaker_db")

    # 1. Nạp Item Similarity
    print("--- 🔄 Đang nạp Item Similarity... ---")
    path_sim = "sneaker-db/gold/item_similarity/"
    files_sim = fs.glob(path_sim + "*.parquet")
    df_sim = pd.concat([pd.read_parquet(fs.open(f)) for f in files_sim])
    df_sim.to_sql('gold_item_similarity', engine, if_exists='replace', index=False)

    # 2. Nạp User Recommendations
    print("--- 🔄 Đang nạp User Recommendations... ---")
    path_rec = "sneaker-db/gold/recommendations/"
    files_rec = fs.glob(path_rec + "*.parquet")
    df_rec = pd.concat([pd.read_parquet(fs.open(f)) for f in files_rec])
    # Chỉ lấy các cột chính để phục vụ Web
    df_rec_final = df_rec[['user_id', 'product_id', 'rank', 'final_score']]
    df_rec_final.to_sql('gold_user_recommendations', engine, if_exists='replace', index=False)

    print("✅ Đã nạp xong bộ não Gold vào Postgres!")

if __name__ == "__main__":
    load_gold_data()