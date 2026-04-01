import pandas as pd
import numpy as np


# LOAD DATA
def load_data():

    interactions = pd.read_csv(
        "data/processed/interactions_clean.csv"
    )

    product_features = pd.read_parquet(
        "data/feature_store/product_features.parquet"
    )

    return interactions, product_features


# JOIN INTERACTIONS + PRODUCT FEATURES
def join_interactions_products(interactions, product_features):

    df = interactions.merge(
        product_features,
        on="product_id",
        how="left"
    )

    return df.copy()


# COMPUTE USER VECTOR
def compute_user_vectors(df):

    exclude_cols = [
    "user_id",
    "product_id",
    "interaction_type",
    "interaction_time",
    "interaction_id",
    "quantity",
    "weight"
    ]

    feature_cols = [c for c in df.columns if c not in exclude_cols]
    feature_df = df[feature_cols].copy()
    weighted_features = feature_df.mul(df["weight"], axis=0)
    user_vectors = weighted_features.groupby(df["user_id"]).sum()
    weight_sum = df.groupby("user_id")["weight"].sum()
    weight_sum = weight_sum.replace(0, 1)
    user_vectors = user_vectors.div(weight_sum, axis=0)
    user_vectors = user_vectors.reset_index()
    return user_vectors


# COMPUTE PRICE PREFERENCE
def compute_price_preference(df):

    price_pref = (
        df.groupby("user_id")["price_scaled"]
        .mean()
        .reset_index()
    )

    price_pref = price_pref.rename(
        columns={"price_scaled": "mean_price_pref"}
    )

    return price_pref


# BUILD USER PROFILES
def build_user_profiles(interactions, product_features):

    print("Joining interactions with product features...")

    df = join_interactions_products(interactions, product_features)

    print("Computing user vectors...")

    user_vectors = compute_user_vectors(df)

    print("Computing price preference...")

    price_pref = compute_price_preference(df)

    print("Combining features...")

    user_profiles = user_vectors.merge(
        price_pref,
        on="user_id",
        how="left"
    )

    return user_profiles


# SAVE USER PROFILES
def save_user_profiles(user_profiles):

    path = "data/feature_store/user_profiles.parquet"

    user_profiles.to_parquet(path, index=False)

    print("Saved user profiles:", path)


# MAIN
def main():

    print("Loading data...")

    interactions, product_features = load_data()

    print("Interactions:", interactions.shape)
    print("Products:", product_features.shape)

    print("Building user profiles...")

    user_profiles = build_user_profiles(
        interactions,
        product_features
    )

    print("User profiles shape:", user_profiles.shape)

    save_user_profiles(user_profiles)

    print("\nSample user profiles:")
    print(user_profiles.head())


if __name__ == "__main__":
    main()