import os
import pandas as pd
import s3fs
from dotenv import load_dotenv


ACTION_MAP = {
    "view": "view",
    "like": "like",
    "addtocart": "add_to_cart",
    "add_to_cart": "add_to_cart",
    "purchase": "purchase"
}


def main():
    load_dotenv()

    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME")

    input_path = f"{bucket_name}/bronze/interactions/*/*.csv"
    output_path = f"s3://{bucket_name}/silver/interactions/interactions_clean.parquet"

    print(f"Reading Bronze interactions from: {input_path}")

    fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret)

    print("Check folder:")
    print(fs.ls(f"{bucket_name}/bronze/interactions/"))

    files = fs.glob(input_path)

    if not files:
        raise ValueError("❌ No interaction files found in S3")

    print(f"Found {len(files)} files")

    df_list = [
        pd.read_csv(f"s3://{file}", storage_options={"key": aws_key, "secret": aws_secret})
        for file in files
    ]

    df = pd.concat(df_list, ignore_index=True)

    if df.empty:
        raise ValueError("❌ DataFrame is empty")

    print("Raw interactions:", len(df))

    # ===== CLEANING =====
    df = df[
        [
            "interaction_id",
            "user_id",
            "product_id",
            "interaction_type",
            "quantity",
            "interaction_time"
        ]
    ].copy()

    df["interaction_id"] = pd.to_numeric(df["interaction_id"], errors="coerce")
    df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["interaction_time"] = pd.to_datetime(df["interaction_time"], errors="coerce")

    df["interaction_type"] = (
        df["interaction_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .map(ACTION_MAP)
        .fillna("unknown")
    )

    df = df.dropna(
        subset=[
            "interaction_id",
            "user_id",
            "product_id",
            "interaction_time"
        ]
    )

    df["quantity"] = df["quantity"].fillna(1).clip(lower=1, upper=100)

    df["interaction_id"] = df["interaction_id"].astype(int)
    df["user_id"] = df["user_id"].astype(int)
    df["product_id"] = df["product_id"].astype(int)
    df["quantity"] = df["quantity"].astype(int)

    df = df.drop_duplicates(
        subset=["user_id", "product_id", "interaction_type", "interaction_time"]
    ).sort_values("interaction_time")

    print("Clean interactions:", len(df))

    # ===== SAVE =====
    df.to_parquet(
        output_path,
        index=False,
        storage_options={"key": aws_key, "secret": aws_secret}
    )

    print("Saved to Silver:", output_path)


if __name__ == "__main__":
    main()