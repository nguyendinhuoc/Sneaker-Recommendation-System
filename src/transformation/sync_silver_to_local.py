import os
import pandas as pd
from dotenv import load_dotenv


def main():
    load_dotenv()

    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME")

    os.makedirs("data/processed", exist_ok=True)

    s3_options = {"key": aws_key, "secret": aws_secret}

    # ===== PRODUCTS =====
    products_input = f"s3://{bucket_name}/silver/products/products_clean.parquet"
    products_output = "data/processed/products_clean.parquet"

    print(f"Downloading products from: {products_input}")
    products = pd.read_parquet(products_input, storage_options=s3_options)
    products.to_parquet(products_output, index=False)
    print(f"Saved local file: {products_output}")

    # ===== USERS =====
    users_input = f"s3://{bucket_name}/silver/users/users_clean.parquet"
    users_output = "data/processed/users_clean.csv"

    print(f"Downloading users from: {users_input}")
    users = pd.read_parquet(users_input, storage_options=s3_options)
    users.to_csv(users_output, index=False)
    print(f"Saved local file: {users_output}")

    # ===== INTERACTIONS =====
    interactions_input = f"s3://{bucket_name}/silver/interactions/interactions_clean.parquet"
    interactions_output = "data/processed/interactions_clean.csv"

    print(f"Downloading interactions from: {interactions_input}")
    interactions = pd.read_parquet(interactions_input, storage_options=s3_options)
    interactions.to_csv(interactions_output, index=False)
    print(f"Saved local file: {interactions_output}")

    print("Sync Silver to local completed!")


if __name__ == "__main__":
    main()