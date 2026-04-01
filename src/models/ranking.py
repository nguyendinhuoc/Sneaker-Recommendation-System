# Recommendation output
import pandas as pd
import numpy as np


# LOAD DATA
def load_data():

    candidates = pd.read_parquet(
        "data/feature_store/user_candidates.parquet"
    )

    products = pd.read_parquet(
        "data/feature_store/product_features.parquet"
    )

    users = pd.read_parquet(
        "data/feature_store/user_profiles.parquet"
    )

    return candidates, products, users


# COMPUTE POPULARITY
def compute_popularity(products):

    products = products.copy()

    products["popularity"] = (
        products["view_count"] + products["purchase_count"]
    )

    max_pop = products["popularity"].max()

    if max_pop > 0:
        products["popularity"] = products["popularity"] / max_pop
    else:
        products["popularity"] = 0

    return products[
        ["product_id", "price_scaled", "popularity"]
    ]


# MERGE DATA
def merge_data(candidates, products, users):

    df = candidates.merge(
        products,
        on="product_id",
        how="left"
    )

    df = df.merge(
        users[["user_id", "mean_price_pref"]],
        on="user_id",
        how="left"
    )

    return df


# PRICE MATCH
def compute_price_match(df):

    df = df.copy()

    df["price_match"] = 1 - abs(
        df["price_scaled"] - df["mean_price_pref"]
    )

    df["price_match"] = df["price_match"].clip(0, 1)

    return df


# CATEGORY MATCH
def compute_category_match(df):

    df = df.copy()

    df["category_match"] = 1

    return df


# FINAL SCORE
def compute_final_score(df):

    df = df.copy()

    df["final_score"] = (
        0.5 * df["similarity"]
        + 0.2 * df["popularity"]
        + 0.2 * df["price_match"]
        + 0.1 * df["category_match"]
    )

    return df


# SIMPLE DIVERSITY FILTER
def apply_diversity(df, max_items_per_user=50):

    df = df.copy()

    df = df.sort_values(
        ["user_id", "final_score"],
        ascending=[True, False]
    )

    df["div_rank"] = df.groupby(
        ["user_id"]
    ).cumcount()

    df = df[df["div_rank"] < max_items_per_user]

    return df


# GET TOP RECOMMENDATIONS
def get_top_recommendations(df, top_k=10):

    df = df.copy()

    df = df.sort_values(
        ["user_id", "final_score"],
        ascending=[True, False]
    )

    df["rank"] = df.groupby("user_id").cumcount() + 1

    df = df[df["rank"] <= top_k]

    return df


# SAVE RESULT
def save_recommendations(df):

    path = "data/feature_store/recommendations.parquet"

    df.to_parquet(path, index=False)

    print("Saved recommendations:", path)


# MAIN 
def main():

    print("Loading data...")

    candidates, products, users = load_data()

    print("Computing popularity...")

    products = compute_popularity(products)

    print("Merging data...")

    df = merge_data(candidates, products, users)

    print("Computing price match...")

    df = compute_price_match(df)

    print("Computing category match...")

    df = compute_category_match(df)

    print("Computing final score...")

    df = compute_final_score(df)

    print("Applying diversity filter...")

    df = apply_diversity(df)

    print("Generating top recommendations...")

    recs = get_top_recommendations(df)

    save_recommendations(recs)

    print("\nSample recommendations:")
    print(recs.head())


if __name__ == "__main__":
    main()