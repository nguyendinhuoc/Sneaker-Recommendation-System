import pandas as pd


def customers_also_viewed(pid):

    interactions = pd.read_csv(
        "data/processed/interactions_clean.csv"
    )

    views = interactions[
        interactions["interaction_type"] == "view"
    ]

    users = views[
        views["product_id"] == pid
    ]["user_id"].unique()

    related = views[
        views["user_id"].isin(users)
    ]

    counts = (
        related["product_id"]
        .value_counts()
        .drop(pid, errors="ignore")
    )

    return counts.head(20)


def customers_also_bought(pid):

    interactions = pd.read_csv(
        "data/processed/interactions_clean.csv"
    )

    buys = interactions[
        interactions["interaction_type"] == "purchase"
    ]

    users = buys[
        buys["product_id"] == pid
    ]["user_id"].unique()

    related = buys[
        buys["user_id"].isin(users)
    ]

    counts = (
        related["product_id"]
        .value_counts()
        .drop(pid, errors="ignore")
    )

    return counts.head(20)