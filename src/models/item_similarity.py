import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# LOAD PRODUCT FEATURES
def load_product_features():

    df = pd.read_parquet(
        "data/feature_store/product_features.parquet"
    )

    return df


# PREPARE FEATURE MATRIX
def prepare_matrix(df):

    product_ids = df["product_id"]

    feature_matrix = df.drop(columns=["product_id"])

    return product_ids, feature_matrix


# COMPUTE COSINE SIMILARITY
def compute_similarity(feature_matrix):

    similarity_matrix = cosine_similarity(feature_matrix)

    return similarity_matrix


# GET TOP SIMILAR PRODUCTS
def get_top_similar(product_ids, similarity_matrix, top_k=10):

    rows = []

    for idx, product_id in enumerate(product_ids):

        scores = similarity_matrix[idx]

        top_indices = np.argsort(scores)[::-1][1:top_k+1]

        for rank, sim_idx in enumerate(top_indices, start=1):

            rows.append({
                "product_id": product_id,
                "similar_product_id": product_ids.iloc[sim_idx],
                "rank": rank,
                "similarity_score": scores[sim_idx]
            })

    return pd.DataFrame(rows)


# SAVE RESULT
def save_similarity(df):

    path = "data/feature_store/item_similarity.parquet"

    df.to_parquet(path, index=False)

    print("Saved item similarity:", path)


# MAIN PIPELINE
def main():

    print("Loading product features...")

    df = load_product_features()

    print("Preparing feature matrix...")

    product_ids, feature_matrix = prepare_matrix(df)

    print("Computing similarity matrix...")

    similarity_matrix = compute_similarity(feature_matrix)

    print("Generating top similar products...")

    similar_df = get_top_similar(product_ids, similarity_matrix)

    save_similarity(similar_df)

    print(similar_df.head())


if __name__ == "__main__":
    main()