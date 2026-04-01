import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# LOAD DATA
def load_data():

    user_profiles = pd.read_parquet(
        "data/feature_store/user_profiles.parquet"
    )

    product_features = pd.read_parquet(
        "data/feature_store/product_features.parquet"
    )

    interactions = pd.read_csv(
        "data/processed/interactions_clean.csv"
    )

    return user_profiles, product_features, interactions


# PREPARE MATRICES
def prepare_matrices(user_profiles, product_features):

    user_ids = user_profiles["user_id"]
    product_ids = product_features["product_id"]

    user_matrix = user_profiles.drop(
        columns=["user_id", "mean_price_pref"]
    )

    product_matrix = product_features.drop(
        columns=["product_id"]
    )

    common_cols = user_matrix.columns.intersection(product_matrix.columns)

    user_matrix = user_matrix[common_cols]
    product_matrix = product_matrix[common_cols]

    return user_ids, user_matrix, product_ids, product_matrix


# COMPUTE SIMILARITY
def compute_similarity(user_matrix, product_matrix):

    similarity_matrix = cosine_similarity(user_matrix, product_matrix)

    return similarity_matrix


# GENERATE CANDIDATES
def generate_candidates(user_ids, product_ids, similarity_matrix, top_k=100):

    rows = []

    for user_idx, user_id in enumerate(user_ids):

        scores = similarity_matrix[user_idx]

        top_indices = np.argsort(scores)[::-1][:top_k]

        for rank, prod_idx in enumerate(top_indices, start=1):

            rows.append({
                "user_id": user_id,
                "product_id": product_ids.iloc[prod_idx],
                "rank": rank,
                "similarity": scores[prod_idx]
            })

    return pd.DataFrame(rows)


# REMOVE INTERACTED ITEMS
def remove_interacted_items(candidates, interactions):

    interacted = interactions[["user_id", "product_id"]]

    candidates = candidates.merge(
        interacted,
        on=["user_id", "product_id"],
        how="left",
        indicator=True
    )

    candidates = candidates[candidates["_merge"] == "left_only"]

    candidates = candidates.drop(columns=["_merge"])

    return candidates


# SAVE
def save_candidates(df):

    path = "data/feature_store/user_candidates.parquet"

    df.to_parquet(path, index=False)

    print("Saved candidates:", path)


# MAIN
def main():

    print("Loading data...")

    user_profiles, product_features, interactions = load_data()

    print("Preparing matrices...")

    user_ids, user_matrix, product_ids, product_matrix = prepare_matrices(
        user_profiles,
        product_features
    )

    print("User matrix shape:", user_matrix.shape)
    print("Product matrix shape:", product_matrix.shape)

    print("Computing user-product similarity...")

    similarity_matrix = compute_similarity(
        user_matrix,
        product_matrix
    )

    print("Generating candidates...")

    candidates = generate_candidates(
        user_ids,
        product_ids,
        similarity_matrix
    )

    print("Removing interacted items...")

    candidates = remove_interacted_items(
        candidates,
        interactions
    )

    save_candidates(candidates)

    print("\nSample candidates:")
    print(candidates.head())


if __name__ == "__main__":
    main()