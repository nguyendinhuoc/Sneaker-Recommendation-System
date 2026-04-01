import os
import pandas as pd
import s3fs
from dotenv import load_dotenv


def main():
    load_dotenv()

    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME")

    input_path = f"{bucket_name}/bronze/users/*/*.csv"
    output_path = f"s3://{bucket_name}/silver/users/users_clean.parquet"

    print(f"Reading Bronze users from: {input_path}")

    fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret)

    files = fs.glob(input_path)

    if not files:
        raise ValueError("❌ No files found in S3 path")

    print(f"Found {len(files)} files")

    df_list = [
        pd.read_csv(f"s3://{file}", storage_options={"key": aws_key, "secret": aws_secret})
        for file in files
    ]

    df = pd.concat(df_list, ignore_index=True)

    if df.empty:
        raise ValueError("❌ DataFrame is empty")

    print("Raw users:", len(df))

    # ===== CLEANING =====
    df = df[["user_id", "name", "gender", "age", "created_at"]].copy()

    df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["gender"] = df["gender"].fillna("").astype(str).str.lower().str.strip()

    df["gender"] = df["gender"].replace({
        "m": "male",
        "male": "male",
        "f": "female",
        "female": "female"
    })

    df["gender"] = df["gender"].where(df["gender"].isin(["male", "female"]), "unknown")

    df = df.dropna(subset=["user_id", "created_at"])
    df = df.drop_duplicates(subset=["user_id"])

    df["user_id"] = df["user_id"].astype(int)

    print("Clean users:", len(df))

    # ===== SAVE =====
    df.to_parquet(
        output_path,
        index=False,
        storage_options={"key": aws_key, "secret": aws_secret}
    )

    print("Saved to Silver:", output_path)


if __name__ == "__main__":
    main()