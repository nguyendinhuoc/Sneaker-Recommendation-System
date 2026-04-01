import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

import pandas as pd
from src.app.interaction_logger import log_interaction
from src.serving.session_recommender import recommend_from_session
from src.serving.collaborative_recommender import (
    customers_also_viewed,
    customers_also_bought
)

TOP_K = 5


# LOAD DATA
def load_data():

    products = pd.read_parquet("data/processed/products_clean.parquet")

    rec = pd.read_parquet(
        "data/feature_store/recommendations.parquet"
    )

    sim = pd.read_parquet(
        "data/feature_store/item_similarity.parquet"
    )

    features = pd.read_parquet(
        "data/feature_store/product_features.parquet"
    )

    if "product_id" in features.columns:
        features = features.set_index("product_id")

    if "popularity" not in products.columns:
        products["popularity"] = products.index[::-1]

    return products, rec, sim, features


# FORMAT PRICE

def format_price(v):

    try:
        return f"{int(v):,} VND"
    except:
        return "N/A"


# PRINT TABLE

def print_products(df):

    print("\n------------------------------------------------------------------------------------------------")
    print(f"{'ID':<6}{'NAME':<45}{'BRAND':<15}{'CATEGORY':<12}{'PRICE':>15}")
    print("------------------------------------------------------------------------------------------------")

    for _, r in df.iterrows():

        name = str(r.get("product_name", "unknown"))[:43]
        brand = str(r.get("brand", "-"))[:13]
        category = str(r.get("category", "-"))[:10]
        price = format_price(r.get("price_vnd", 0))

        print(
            f"{int(r['product_id']):<6}"
            f"{name:<45}"
            f"{brand:<15}"
            f"{category:<12}"
            f"{price:>15}"
        )

    print("------------------------------------------------------------------------------------------------")

# GET PRODUCTS

def get_products(products, product_ids, current_pid=None):

    rows = []

    for pid in product_ids:

        if current_pid and pid == current_pid:
            continue

        prod = products[products["product_id"] == pid]

        if not prod.empty:
            rows.append(prod.iloc[0])

        if len(rows) >= TOP_K:
            break

    return pd.DataFrame(rows)

# PRODUCT DETAIL

def show_product_detail(products, pid):

    p = products[products["product_id"] == pid]

    if p.empty:
        print("\n❌ Product not found")
        return False

    p = p.iloc[0]

    print("\n=====================")
    print("📦 PRODUCT DETAIL")
    print("=====================")

    print("ID       :", p["product_id"])
    print("Name     :", p.get("product_name", "-"))
    print("Brand    :", p.get("brand", "-"))
    print("Category :", p.get("category", "-"))
    print("Material :", p.get("material", "-"))
    print("Purpose  :", p.get("purpose", "-"))
    print("Price    :", format_price(p.get("price_vnd", 0)))

    return True


# RELATED PRODUCTS

def show_related(similarity, products, pid):

    print("\n🔗 RELATED PRODUCTS")

    sim = similarity[
        similarity["product_id"] == pid
    ].sort_values("rank")

    product_ids = sim["similar_product_id"].tolist()

    df = get_products(products, product_ids, pid)

    if not df.empty:
        print_products(df)


# ALSO VIEWED

def show_also_viewed(products, pid):

    rec = customers_also_viewed(pid)

    if rec is None:
        return

    print("\n👥 CUSTOMERS ALSO VIEWED")

    product_ids = rec.index.tolist()

    df = get_products(products, product_ids, pid)

    if not df.empty:
        print_products(df)


# ALSO BOUGHT

def show_also_bought(products, pid):

    rec = customers_also_bought(pid)

    if rec is None:
        return

    print("\n🛒 CUSTOMERS ALSO BOUGHT")

    product_ids = rec.index.tolist()

    df = get_products(products, product_ids, pid)

    if not df.empty:
        print_products(df)


# SESSION REC

def show_session_rec(user_id, features, products, pid):

    rec = recommend_from_session(user_id, features)

    if rec is None:
        return

    print("\n⚡ SESSION-BASED RECOMMENDATIONS")

    product_ids = rec.index.tolist()

    df = get_products(products, product_ids, pid)

    if not df.empty:
        print_products(df)


# USER REC

def show_user_rec(rec, products, user_id, pid):

    print("\n⭐ RECOMMENDED FOR YOU")

    r = rec[
        rec["user_id"] == user_id
    ].sort_values("final_score", ascending=False)

    product_ids = r["product_id"].tolist()

    df = get_products(products, product_ids, pid)

    if not df.empty:
        print_products(df)


# POPULAR PRODUCTS

def show_popular(products):

    print("\n🔥 POPULAR PRODUCTS")

    df = products.sort_values(
        "popularity",
        ascending=False
    ).head(TOP_K)

    print_products(df)


# HOMEPAGE

def browse_homepage(products):

    page_size = 20
    page = 0

    sorted_products = products.sort_values(
        "popularity",
        ascending=False
    ).reset_index(drop=True)

    while True:

        start = page * page_size
        end = start + page_size

        page_df = sorted_products.iloc[start:end]

        print(f"\n🏠 HOMEPAGE — Page {page+1}")

        print_products(page_df)

        print("\nOptions:")
        print("n → next page")
        print("p → previous page")
        print("v → view product")
        print("q → menu")

        choice = input("\nSelect option: ").strip()

        if choice == "n":

            if end < len(sorted_products):
                page += 1
            else:
                print("No more pages")

        elif choice == "p":

            if page > 0:
                page -= 1

        elif choice == "v":

            try:
                pid = int(input("Enter product id: "))
                return pid
            except:
                print("Invalid product id")

        elif choice == "q":

            return None


# PRODUCT LOOP

def product_loop(products, rec, sim, features, user_id, pid):

    while True:

        ok = show_product_detail(products, pid)

        if not ok:
            return

        log_interaction(user_id, pid, "view")

        show_related(sim, products, pid)

        show_also_viewed(products, pid)

        show_also_bought(products, pid)

        show_session_rec(
            user_id,
            features,
            products,
            pid
        )

        show_user_rec(
            rec,
            products,
            user_id,
            pid
        )

        show_popular(products)

        print("\nOptions:")
        print("1 → View another product")
        print("2 → Back to homepage")
        print("3 → Purchase product")
        print("4 → Exit")

        choice = input("Select option: ")

        if choice == "1":

            try:
                pid = int(input("Enter product id: "))
                continue
            except:
                print("Invalid id")

        elif choice == "2":
            return

        elif choice == "3":

            log_interaction(user_id, pid, "purchase")
            print("\n🛒 Purchase recorded")

        elif choice == "4":

            print("\nExit demo")
            exit()


# MAIN
def main():

    products, rec, sim, features = load_data()

    print("\n🔐 LOGIN")

    try:
        user_id = int(input("Enter user id: "))
    except:
        print("Invalid user id")
        return

    while True:

        pid = browse_homepage(products)

        if pid is None:

            print("\nMenu:")
            print("1 → Show recommendations")
            print("2 → Back to homepage")
            print("3 → Exit")

            choice = input("Select option: ")

            if choice == "1":

                show_session_rec(
                    user_id,
                    features,
                    products,
                    None
                )

                show_user_rec(
                    rec,
                    products,
                    user_id,
                    None
                )

                show_popular(products)

            elif choice == "2":
                continue

            elif choice == "3":
                print("\nExit demo")
                break

        else:

            product_loop(
                products,
                rec,
                sim,
                features,
                user_id,
                pid
            )


if __name__ == "__main__":
    main()