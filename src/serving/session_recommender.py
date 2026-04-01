import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


SESSION_FILE = "data/session/session_interactions.csv"


ACTION_WEIGHTS = {
    "view": 1,
    "like": 2,
    "add_to_cart": 3,
    "purchase": 5
}


def load_session_interactions():

    try:
        df = pd.read_csv(SESSION_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(
            columns=["user_id", "product_id", "action", "timestamp"]
        )

    return df


def build_session_vector(user_id, product_features):

    interactions = load_session_interactions()

    session = interactions[interactions["user_id"] == user_id]

    if session.empty:
        return None

    vectors = []
    weights = []

    for _, row in session.iterrows():

        pid = row["product_id"]
        action = row["action"]

        if pid not in product_features.index:
            continue

        weight = ACTION_WEIGHTS.get(action, 1)

        vectors.append(product_features.loc[pid].values)
        weights.append(weight)

    if len(vectors) == 0:
        return None

    vectors = np.array(vectors)
    weights = np.array(weights)

    session_vector = np.average(vectors, axis=0, weights=weights)

    return session_vector


def recommend_from_session(user_id, product_features, top_k=10):

    session_vector = build_session_vector(user_id, product_features)

    if session_vector is None:
        return None

    product_matrix = product_features.values

    sims = cosine_similarity(
        session_vector.reshape(1, -1),
        product_matrix
    )[0]

    product_features["score"] = sims

    recs = (
        product_features
        .sort_values("score", ascending=False)
        .head(top_k)
    )

    return recs