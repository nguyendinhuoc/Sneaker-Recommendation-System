import subprocess
import sys


def run_step(script_path, step_name):
    print(f"\n=== Running: {step_name} ===")
    subprocess.run([sys.executable, script_path], check=True)
    print(f"=== Done: {step_name} ===")


def main():
    run_step("src/ingestion/uploader.py", "Upload users/interactions to Bronze")
    run_step("src/transformation/silver_users.py", "Build Silver users")
    run_step("src/transformation/silver_interactions.py", "Build Silver interactions")
    run_step("src/transformation/silver_cleaning.py", "Build Silver products")
    run_step("src/transformation/sync_silver_to_local.py", "Sync Silver to local")
    run_step("pipelines/run_pipeline.py", "Build feature store and recommendations")
    run_step("src/serving/publish_gold.py", "Publish Gold to S3")

    print("\nEND-TO-END PIPELINE COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()