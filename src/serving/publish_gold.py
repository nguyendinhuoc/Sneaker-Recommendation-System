import os
import boto3
from dotenv import load_dotenv


UPLOAD_PLAN = [
    ("data/feature_store/product_features.parquet", "gold/product_features"),
    ("data/feature_store/user_profiles.parquet", "gold/user_profiles"),
    ("data/feature_store/item_similarity.parquet", "gold/item_similarity"),
    ("data/feature_store/user_candidates.parquet", "gold/user_candidates"),
    ("data/feature_store/recommendations.parquet", "gold/recommendations"),
]


def main():
    load_dotenv()

    bucket_name = os.getenv("S3_BUCKET_NAME")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret
    )

    for local_path, s3_folder in UPLOAD_PLAN:
        if not os.path.exists(local_path):
            print(f"Missing file, skipped: {local_path}")
            continue

        filename = os.path.basename(local_path)
        s3_key = f"{s3_folder}/{filename}"

        print(f"Uploading {local_path} -> s3://{bucket_name}/{s3_key}")
        s3.upload_file(local_path, bucket_name, s3_key)

    print("Publish Gold completed!")


if __name__ == "__main__":
    main()