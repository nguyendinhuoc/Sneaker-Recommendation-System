import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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

TOP_K_PER_USER = 300
MIN_CANDIDATE_SCORE = 0.03
GLOBAL_POPULARITY_WEIGHT = 0.12


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
    df["score"] = df["score"].round(2)
    df["score"] = df["score"].clip(0, 100)  
    return df


def load_products(engine):
    query = """
        SELECT
            product_id,
            brand,
            category,
            type,
            purpose
        FROM products
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    df["product_id"] = df["product_id"].astype(str)
    for col in ["brand", "category", "type", "purpose"]:
        df[col] = df[col].fillna("").astype(str).str.strip().str.lower()
    return df


def load_item_similarity(engine):
    query = """
        SELECT
            product_id,
            similar_product_id,
            rank,
            similarity_score
        FROM gold_item_similarity
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame(columns=["product_id", "similar_product_id", "rank", "similarity_score"])

    if df.empty:
        return df

    df["product_id"] = df["product_id"].astype(str)
    df["similar_product_id"] = df["similar_product_id"].astype(str)
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(999).astype(int)
    df["similarity_score"] = pd.to_numeric(df["similarity_score"], errors="coerce").fillna(0.0)
    return df


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


def build_user_feature_profiles(scored_df, product_df):
    merged = scored_df.merge(product_df, on="product_id", how="left")

    brand_profile = (
        merged[merged["brand"] != ""]
        .groupby(["user_id", "brand"], as_index=False)["score"]
        .sum()
        .rename(columns={"score": "brand_score"})
    )

    category_profile = (
        merged[merged["category"] != ""]
        .groupby(["user_id", "category"], as_index=False)["score"]
        .sum()
        .rename(columns={"score": "category_score"})
    )

    type_profile = (
        merged[merged["type"] != ""]
        .groupby(["user_id", "type"], as_index=False)["score"]
        .sum()
        .rename(columns={"score": "type_score"})
    )

    purpose_profile = (
        merged[merged["purpose"] != ""]
        .groupby(["user_id", "purpose"], as_index=False)["score"]
        .sum()
        .rename(columns={"score": "purpose_score"})
    )

    return brand_profile, category_profile, type_profile, purpose_profile


def generate_candidate_scores(scored_df, similarity_df):
    if scored_df.empty or similarity_df.empty:
        return pd.DataFrame(columns=["user_id", "product_id", "score"])

    candidates = scored_df.merge(similarity_df, on="product_id", how="inner")
    candidates["score"] = (
        candidates["score"]
        * candidates["similarity_score"]
        * (1 + 1 / np.sqrt(candidates["rank"].clip(lower=1)))
    )

    candidates = (
        candidates.groupby(["user_id", "similar_product_id"], as_index=False)["score"]
        .sum()
        .rename(columns={"similar_product_id": "product_id"})
    )

    return candidates


def apply_feature_boosts(candidate_df, product_df, brand_profile, category_profile, type_profile, purpose_profile):
    if candidate_df.empty:
        return candidate_df

    ranked = candidate_df.merge(product_df, on="product_id", how="left")

    ranked = ranked.merge(brand_profile, on=["user_id", "brand"], how="left")
    ranked = ranked.merge(category_profile, on=["user_id", "category"], how="left")
    ranked = ranked.merge(type_profile, on=["user_id", "type"], how="left")
    ranked = ranked.merge(purpose_profile, on=["user_id", "purpose"], how="left")

    ranked["brand_score"] = ranked["brand_score"].fillna(0.0)
    ranked["category_score"] = ranked["category_score"].fillna(0.0)
    ranked["type_score"] = ranked["type_score"].fillna(0.0)
    ranked["purpose_score"] = ranked["purpose_score"].fillna(0.0)

    ranked["score"] = (
        ranked["score"]
        + ranked["brand_score"] * 0.18
        + ranked["category_score"] * 0.12
        + ranked["type_score"] * 0.08
        + ranked["purpose_score"] * 0.06
    )

    return ranked[["user_id", "product_id", "score"]]


def remove_seen_items(candidate_df, scored_df):
    if candidate_df.empty:
        return candidate_df

    seen_pairs = set(zip(scored_df["user_id"], scored_df["product_id"]))
    filtered = candidate_df[
        ~candidate_df.apply(lambda row: (row["user_id"], row["product_id"]) in seen_pairs, axis=1)
    ].copy()
    return filtered


def build_fallback_rankings(scored_df, product_df, brand_profile, category_profile, type_profile, purpose_profile):
    users = scored_df["user_id"].astype(str).unique().tolist()
    products = product_df["product_id"].astype(str).unique().tolist()

    if not users or not products:
        return pd.DataFrame(columns=["user_id", "product_id", "score"])

    user_frame = pd.DataFrame({"user_id": users})
    product_frame = product_df.copy()

    cross = (
        user_frame.assign(key=1)
        .merge(product_frame.assign(key=1), on="key", how="inner")
        .drop(columns=["key"])
    )

    cross = cross.merge(brand_profile, on=["user_id", "brand"], how="left")
    cross = cross.merge(category_profile, on=["user_id", "category"], how="left")
    cross = cross.merge(type_profile, on=["user_id", "type"], how="left")
    cross = cross.merge(purpose_profile, on=["user_id", "purpose"], how="left")

    for col in ["brand_score", "category_score", "type_score", "purpose_score"]:
        cross[col] = cross[col].fillna(0.0)

    cross["score"] = (
        cross["brand_score"] * 0.25
        + cross["category_score"] * 0.16
        + cross["type_score"] * 0.11
        + cross["purpose_score"] * 0.08
    )

    return cross[["user_id", "product_id", "score"]].copy()


def compute_global_popularity(scored_df):
    if scored_df.empty:
        return pd.DataFrame(columns=["product_id", "popularity_score"])

    popularity = (
        scored_df.groupby("product_id", as_index=False)["score"]
        .sum()
        .rename(columns={"score": "popularity_score"})
    )

    max_val = popularity["popularity_score"].max()
    if pd.notna(max_val) and max_val > 0:
        popularity["popularity_score"] = popularity["popularity_score"] / max_val
    else:
        popularity["popularity_score"] = 0.0

    return popularity


def normalize_scores(df):
    if df.empty:
        return df

    def _normalize(series):
        min_val = series.min()
        max_val = series.max()
        if pd.isna(min_val) or pd.isna(max_val) or max_val <= min_val:
            return pd.Series([0.0] * len(series), index=series.index)
        return ((series - min_val) / (max_val - min_val + 1e-9)) * 100.0

    df["score"] = df.groupby("user_id")["score"].transform(_normalize)
    df["score"] = df["score"].round(2)
    df["score"] = df["score"].clip(0, 100)
    return df


def rank_per_user(candidate_df):
    if candidate_df.empty:
        return pd.DataFrame(columns=["user_id", "product_id", "score", "rank"])

    candidate_df = candidate_df[candidate_df["score"] >= MIN_CANDIDATE_SCORE].copy()
    if candidate_df.empty:
        return pd.DataFrame(columns=["user_id", "product_id", "score", "rank"])

    candidate_df["score"] = candidate_df["score"].round(6)
    candidate_df = candidate_df.sort_values(["user_id", "score", "product_id"], ascending=[True, False, True])

    candidate_df["rank"] = candidate_df.groupby("user_id").cumcount() + 1
    candidate_df = candidate_df[candidate_df["rank"] <= TOP_K_PER_USER].copy()
    return candidate_df


def atomic_replace_table(engine, df, target_table: str):
    staging_table = f"{target_table}_staging"

    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))
        df.to_sql(staging_table, conn, if_exists="replace", index=False)
        conn.execute(text(f'DROP TABLE IF EXISTS "{target_table}"'))
        conn.execute(text(f'ALTER TABLE "{staging_table}" RENAME TO "{target_table}"'))


def train_user_recommendations():
    print("--- TRAIN GOLD USER RECOMMENDATIONS ---")
    engine = build_engine()

    print("1. Đang đọc interactions thật...")
    interactions_df = load_interactions(engine)
    if interactions_df.empty:
        print("Không có interaction thật để train.")
        return

    print("2. Đang đọc products...")
    product_df = load_products(engine)
    if product_df.empty:
        print("Không có products trong catalog.")
        return

    print("3. Đang đọc gold_item_similarity...")
    similarity_df = load_item_similarity(engine)

    print("4. Đang chấm điểm hành vi user-item...")
    scored_df = score_interactions(interactions_df)
    if scored_df.empty:
        print("Không đủ dữ liệu score để train.")
        return

    print("5. Đang xây user preference profile...")
    brand_profile, category_profile, type_profile, purpose_profile = build_user_feature_profiles(
        scored_df,
        product_df,
    )

    print("6. Đang sinh candidate từ item similarity...")
    candidate_df = generate_candidate_scores(scored_df, similarity_df)

    print("7. Đang boost theo brand/category/type/purpose...")
    candidate_df = apply_feature_boosts(
        candidate_df,
        product_df,
        brand_profile,
        category_profile,
        type_profile,
        purpose_profile,
    )

    print("8. Đang loại item user đã tương tác...")
    candidate_df = remove_seen_items(candidate_df, scored_df)

    print("9. Đang tính global popularity boost...")
    popularity_df = compute_global_popularity(scored_df)
    if not candidate_df.empty:
        candidate_df = candidate_df.merge(popularity_df, on="product_id", how="left")
        candidate_df["popularity_score"] = candidate_df["popularity_score"].fillna(0.0)
        candidate_df["score"] = candidate_df["score"] + candidate_df["popularity_score"] * GLOBAL_POPULARITY_WEIGHT
        candidate_df = candidate_df[["user_id", "product_id", "score"]]

    print("10. Đang bổ sung fallback theo hồ sơ hành vi nếu candidate còn mỏng...")
    fallback_df = build_fallback_rankings(
        scored_df,
        product_df,
        brand_profile,
        category_profile,
        type_profile,
        purpose_profile,
    )
    fallback_df = remove_seen_items(fallback_df, scored_df)
    if not fallback_df.empty:
        fallback_df = fallback_df.merge(popularity_df, on="product_id", how="left")
        fallback_df["popularity_score"] = fallback_df["popularity_score"].fillna(0.0)
        fallback_df["score"] = fallback_df["score"] + fallback_df["popularity_score"] * (GLOBAL_POPULARITY_WEIGHT * 0.7)
        fallback_df = fallback_df[["user_id", "product_id", "score"]]

    combined_df = pd.concat([candidate_df, fallback_df], ignore_index=True)
    if combined_df.empty:
        print("Không tạo được candidate nào.")
        return

    combined_df = combined_df.groupby(["user_id", "product_id"], as_index=False)["score"].max()

    print("11. Đang normalize score theo từng user...")
    combined_df = normalize_scores(combined_df)

    print("12. Đang rank top sản phẩm cho từng user...")
    final_df = rank_per_user(combined_df)

    if final_df.empty:
        print("Không tạo được gold_user_recommendations.")
        return

    print("13. Đang atomic swap bảng gold_user_recommendations...")
    atomic_replace_table(engine, final_df, "gold_user_recommendations")

    print(f"Hoàn tất: {len(final_df)} dòng")
    print(f"Số user có ranking: {final_df['user_id'].nunique()}")
    print(f"Số product được recommend: {final_df['product_id'].nunique()}")


if __name__ == "__main__":
    train_user_recommendations()
