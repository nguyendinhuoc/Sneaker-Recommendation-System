def recommend_popular(products, top_k=10):
    """
    Recommend sản phẩm phổ biến
    """

    if "popularity" not in products.columns:
        raise ValueError("products must contain popularity column")

    recs = (
        products
        .sort_values("popularity", ascending=False)
        .head(top_k)
    )

    return recs