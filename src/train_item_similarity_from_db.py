import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

BASE_SCORES = {
    "view": 0.5,
    "like": 2.0,
    "add_to_cart": 5.0,
    "purchase": 9.0,
}

EVENT_CAPS = {
    "view": 2.0,
    "like": 4.0,
    "add_to_cart": 8.0,
    "purchase": 12.0,
}

TOP_K = 24
MIN_SIMILARITY = 0.06


def build_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL không tồn tại trong môi trường")
    return create_engine(db_url)


def load_interactions(engine):
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
    if df.empty:
        return df

    df["user_id"] = df["user_id"].astype(str)
    df["product_id"] = df["product_id"].astype(str)
    df["interaction_type"] = df["interaction_type"].astype(str).str.strip().str.lower()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).clip(lower=1)
    df["interaction_time"] = pd.to_datetime(df["interaction_time"], errors="coerce")
    return df


def load_products(engine):
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
    if product_df.empty:
        return product_df

    product_df["product_id"] = product_df["product_id"].astype(str)

    metadata_cols = ["name", "brand", "category", "style", "type", "purpose", "color", "material"]
    for col in metadata_cols:
        product_df[col] = product_df[col].fillna("").astype(str).str.strip().str.lower()

    product_df["content_text"] = (
        product_df["name"] + " "
        + product_df["brand"] + " "
        + product_df["category"] + " "
        + product_df["style"] + " "
        + product_df["type"] + " "
        + product_df["purpose"] + " "
        + product_df["color"] + " "
        + product_df["material"]
    ).str.strip()

    return product_df


def score_interactions(df):
    if df.empty:
        return pd.DataFrame(columns=["user_id", "product_id", "score"])

    scored = df.copy()
    scored["base_score"] = scored["interaction_type"].map(BASE_SCORES).fillna(0.0)
    scored = scored[scored["base_score"] > 0].copy()

    strong_mask = scored["interaction_type"].isin(["add_to_cart", "purchase"])
    scored["quantity_factor"] = 1.0
    scored.loc[strong_mask, "quantity_factor"] = 1 + 0.15 * (
        scored.loc[strong_mask, "quantity"].clip(upper=5) - 1
    )

    latest_time = scored["interaction_time"].max()
    if pd.notna(latest_time):
        days_diff = (latest_time - scored["interaction_time"]).dt.days.fillna(0).clip(lower=0)
        scored["time_decay"] = 0.5 ** (days_diff / 30.0)
    else:
        scored["time_decay"] = 1.0

    scored["score"] = scored["base_score"] * scored["quantity_factor"] * scored["time_decay"]

    grouped = (
        scored.groupby(["user_id", "product_id", "interaction_type"], as_index=False)["score"]
        .sum()
    )

    grouped["score"] = grouped.apply(
        lambda row: min(row["score"], EVENT_CAPS.get(row["interaction_type"], row["score"])),
        axis=1,
    )

    grouped = grouped.groupby(["user_id", "product_id"], as_index=False)["score"].sum()
    return grouped


def compute_behavior_similarity(scored_df):
    if scored_df.empty:
        return pd.DataFrame()

    user_item_matrix = scored_df.pivot(
        index="user_id",
        columns="product_id",
        values="score",
    ).fillna(0)

    item_user_matrix = user_item_matrix.T
    similarity_matrix = cosine_similarity(item_user_matrix)

    return pd.DataFrame(
        similarity_matrix,
        index=item_user_matrix.index.astype(str),
        columns=item_user_matrix.index.astype(str),
    )


def compute_content_similarity(product_df):
    if product_df.empty:
        return pd.DataFrame()

    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    content_vectors = tfidf.fit_transform(product_df["content_text"])

    similarity_matrix = cosine_similarity(content_vectors)

    return pd.DataFrame(
        similarity_matrix,
        index=product_df["product_id"].astype(str),
        columns=product_df["product_id"].astype(str),
    )


def merge_hybrid_similarity(behavior_sim_df, content_sim_df):
    all_product_ids = sorted(
        set(behavior_sim_df.index.astype(str)).union(set(content_sim_df.index.astype(str)))
    )

    if not all_product_ids:
        return pd.DataFrame()

    behavior_sim_df = behavior_sim_df.reindex(
        index=all_product_ids,
        columns=all_product_ids,
        fill_value=0.0,
    )
    content_sim_df = content_sim_df.reindex(
        index=all_product_ids,
        columns=all_product_ids,
        fill_value=0.0,
    )

    return 0.72 * behavior_sim_df + 0.28 * content_sim_df


def build_item_recommendations(hybrid_sim_df):
    recommendations = []

    if hybrid_sim_df.empty:
        return pd.DataFrame(columns=["product_id", "similar_product_id", "rank", "similarity_score"])

    for product_id in hybrid_sim_df.index:
        similar_scores = hybrid_sim_df[product_id].sort_values(ascending=False)
        similar_scores = similar_scores[similar_scores.index != product_id]
        similar_scores = similar_scores[similar_scores >= MIN_SIMILARITY].head(TOP_K)

        for rank, (sim_id, sim_score) in enumerate(similar_scores.items(), start=1):
            recommendations.append(
                {
                    "product_id": str(product_id),
                    "similar_product_id": str(sim_id),
                    "rank": rank,
                    "similarity_score": round(float(sim_score), 6),
                }
            )

    return pd.DataFrame(recommendations)


def atomic_replace_table(engine, df, target_table: str):
    staging_table = f"{target_table}_staging"

    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))
        df.to_sql(staging_table, conn, if_exists="replace", index=False)
        conn.execute(text(f'DROP TABLE IF EXISTS "{target_table}"'))
        conn.execute(text(f'ALTER TABLE "{staging_table}" RENAME TO "{target_table}"'))


def train_item_based_model():
    print("--- TRAIN GOLD ITEM SIMILARITY ---")
    engine = build_engine()

    print("1. Đang đọc interactions thật từ Neon...")
    interactions_df = load_interactions(engine)

    print("2. Đang đọc catalog sản phẩm...")
    product_df = load_products(engine)

    if product_df.empty:
        print("Không có products trong catalog.")
        return

    print("3. Đang chấm điểm hành vi...")
    scored_df = score_interactions(interactions_df)

    if scored_df.empty:
        print("Không có đủ interactions thật, fallback sang content-only similarity.")

    print("4. Đang tính behavior similarity...")
    behavior_sim_df = compute_behavior_similarity(scored_df)

    print("5. Đang tính content similarity...")
    content_sim_df = compute_content_similarity(product_df)

    print("6. Đang gộp thành hybrid similarity...")
    hybrid_sim_df = merge_hybrid_similarity(behavior_sim_df, content_sim_df)

    print("7. Đang tạo top similar items...")
    final_df = build_item_recommendations(hybrid_sim_df)

    if final_df.empty:
        print("Dữ liệu chưa đủ để tạo gold_item_similarity.")
        return

    print("8. Đang atomic swap bảng gold_item_similarity...")
    atomic_replace_table(engine, final_df, "gold_item_similarity")

    print(f"Hoàn tất: {len(final_df)} dòng")
    print(f"Số sản phẩm có similarity: {final_df['product_id'].nunique()}")


if __name__ == "__main__":
    train_item_based_model()