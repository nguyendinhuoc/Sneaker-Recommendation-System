import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import os
from dotenv import load_dotenv

load_dotenv()


def train_item_based_model():
    print("--- KHỞI ĐỘNG VÒNG LẶP AI ---")

    # 1. Kết nối Database
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL không tồn tại trong file .env")
    engine = create_engine(db_url)

    # 2. Lấy dữ liệu interactions
    print("1. Đang lấy dữ liệu hành vi người dùng...")
    query = """
        SELECT
            user_id,
            product_id,
            interaction_type,
            COALESCE(quantity, 1) AS quantity,
            interaction_time
        FROM interactions
        WHERE interaction_type IN ('view', 'like', 'add_to_cart', 'purchase')
    """
    df = pd.read_sql(query, engine)

    # 2b. Lấy metadata sản phẩm
    print("1b. Đang lấy metadata sản phẩm...")
    product_query = """
        SELECT
            product_id,
            name,
            brand,
            category,
            style,
            type,
            purpose,
            color,
            material
        FROM products
    """
    product_df = pd.read_sql(product_query, engine)

    if df.empty:
        print("Chưa có tương tác nào. Hãy lên Web click xem và mua vài đôi giày trước nhé!")
        return

    if product_df.empty:
        print("Không có dữ liệu products để tính content similarity.")
        return

    # 3. Chuẩn hóa dữ liệu interactions
    df["user_id"] = df["user_id"].astype(str)
    df["product_id"] = df["product_id"].astype(str)
    df["interaction_type"] = df["interaction_type"].astype(str).str.strip().str.lower()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).clip(lower=1)
    df["interaction_time"] = pd.to_datetime(df["interaction_time"], errors="coerce")

    print("Tổng số interactions dùng để train:", len(df))
    print("Phân bố interaction type:")
    print(df["interaction_type"].value_counts())
    print("Số user:", df["user_id"].nunique())
    print("Số product trong interactions:", df["product_id"].nunique())
    print("Tổng số product trong catalog:", product_df["product_id"].nunique())

    # 4. Chuẩn hóa metadata sản phẩm
    product_df["product_id"] = product_df["product_id"].astype(str)

    metadata_cols = ["name", "brand", "category", "style", "type", "purpose", "color", "material"]
    for col in metadata_cols:
        product_df[col] = product_df[col].fillna("").astype(str).str.strip().str.lower()

    product_df["content_text"] = (
        product_df["name"] + " " +
        product_df["brand"] + " " +
        product_df["category"] + " " +
        product_df["style"] + " " +
        product_df["type"] + " " +
        product_df["purpose"] + " " +
        product_df["color"] + " " +
        product_df["material"]
    ).str.strip()

    # 5. Chấm điểm interactions
    print("2. Đang chấm điểm interaction với time decay + quantity cap...")

    base_scores = {
        "view": 0.5,
        "like": 2.0,
        "add_to_cart": 5.0,
        "purchase": 9.0,
    }

    df["base_score"] = df["interaction_type"].map(base_scores).fillna(0.0)
    df = df[df["base_score"] > 0].copy()

    # quantity chỉ nên tăng điểm ở event mạnh
    df["quantity_factor"] = 1.0
    strong_mask = df["interaction_type"].isin(["add_to_cart", "purchase"])
    df.loc[strong_mask, "quantity_factor"] = 1 + 0.15 * (
        df.loc[strong_mask, "quantity"].clip(upper=5) - 1
    )

    # time decay
    latest_time = df["interaction_time"].max()
    if pd.notna(latest_time):
        days_diff = (latest_time - df["interaction_time"]).dt.days.fillna(0).clip(lower=0)
        df["time_decay"] = 0.5 ** (days_diff / 30.0)
    else:
        df["time_decay"] = 1.0

    df["score"] = df["base_score"] * df["quantity_factor"] * df["time_decay"]

    # cap theo loại event để tránh spam
    event_caps = {
        "view": 2.0,
        "like": 4.0,
        "add_to_cart": 8.0,
        "purchase": 12.0,
    }

    df_grouped = (
        df.groupby(["user_id", "product_id", "interaction_type"], as_index=False)["score"]
        .sum()
    )

    df_grouped["score"] = df_grouped.apply(
        lambda row: min(row["score"], event_caps.get(row["interaction_type"], row["score"])),
        axis=1
    )

    df_grouped = (
        df_grouped.groupby(["user_id", "product_id"], as_index=False)["score"]
        .sum()
    )

    # 6. Tạo user-item matrix
    print("3. Đang xây dựng ma trận user-item...")
    user_item_matrix = df_grouped.pivot(
        index="user_id",
        columns="product_id",
        values="score"
    ).fillna(0)

    print(f"Kích thước user-item matrix: {user_item_matrix.shape}")

    # 7. Behavior similarity
    print("4. Đang tính behavior similarity từ interactions...")
    item_user_matrix = user_item_matrix.T
    behavior_similarity_matrix = cosine_similarity(item_user_matrix)

    behavior_sim_df = pd.DataFrame(
        behavior_similarity_matrix,
        index=item_user_matrix.index.astype(str),
        columns=item_user_matrix.index.astype(str)
    )

    # 8. Content similarity
    print("4b. Đang tính content similarity từ metadata...")
    tfidf = TfidfVectorizer()
    content_vectors = tfidf.fit_transform(product_df["content_text"])

    content_similarity_matrix = cosine_similarity(content_vectors)

    content_sim_df = pd.DataFrame(
        content_similarity_matrix,
        index=product_df["product_id"].astype(str),
        columns=product_df["product_id"].astype(str)
    )

    # 9. Gộp hybrid similarity
    print("4c. Đang gộp behavior + content similarity...")

    all_product_ids = sorted(
        set(behavior_sim_df.index.astype(str)).union(set(content_sim_df.index.astype(str)))
    )

    behavior_sim_df = behavior_sim_df.reindex(
        index=all_product_ids,
        columns=all_product_ids,
        fill_value=0.0
    )

    content_sim_df = content_sim_df.reindex(
        index=all_product_ids,
        columns=all_product_ids,
        fill_value=0.0
    )

    # Trọng số hybrid
    hybrid_sim_df = 0.7 * behavior_sim_df + 0.3 * content_sim_df

    # 10. Lấy top similar items cho mỗi product
    print("5. Đang chọn lọc Top gợi ý tốt nhất...")

    recommendations = []

    MIN_SIMILARITY = 0.08
    TOP_K = 16

    for product_id in hybrid_sim_df.index:
        similar_scores = hybrid_sim_df[product_id].sort_values(ascending=False)
        similar_scores = similar_scores[similar_scores.index != product_id]
        similar_scores = similar_scores[similar_scores >= MIN_SIMILARITY]

        top_k = similar_scores.head(TOP_K)

        rank = 1
        for sim_id, sim_score in top_k.items():
            recommendations.append({
                "product_id": str(product_id),
                "similar_product_id": str(sim_id),
                "rank": rank,
                "similarity_score": round(float(sim_score), 4),
            })
            rank += 1

    # 11. Lưu xuống gold_item_similarity
    if recommendations:
        print("6. Đang lưu bộ não mới lên tầng Gold...")
        final_df = pd.DataFrame(recommendations)

        final_df["product_id"] = final_df["product_id"].astype(str)
        final_df["similar_product_id"] = final_df["similar_product_id"].astype(str)

        final_df.to_sql("gold_item_similarity", engine, if_exists="replace", index=False)

        print(f"HOÀN TẤT! Đã tạo ra {len(final_df)} cặp gợi ý hybrid.")
        print(f"Số sản phẩm có item-similarity: {final_df['product_id'].nunique()}")
    else:
        print("Dữ liệu chưa đủ để tạo ra item similarity.")


if __name__ == "__main__":
    train_item_based_model()