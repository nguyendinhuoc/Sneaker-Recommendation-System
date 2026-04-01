import os
import subprocess
import sys


def clean_old_files():
    folders = [
        "data/processed",
        "data/feature_store"
    ]

    for folder in folders:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                path = os.path.join(folder, file)
                if os.path.isfile(path):
                    os.remove(path)

    print("Old files removed")


def run_step(script_path, step_name):
    print(f"Running {step_name}...")
    subprocess.run(
        [sys.executable, script_path],
        check=True
    )


def run_pipeline():
    run_step("src/transformation/preprocessing.py", "preprocessing")
    run_step("src/features/feature_engineering.py", "feature engineering")
    run_step("src/features/user_profile.py", "user profiling")
    run_step("src/models/item_similarity.py", "item similarity")
    run_step("src/models/candidate_generation.py", "candidate generation")
    run_step("src/models/ranking.py", "ranking")

    print("Pipeline completed successfully")


if __name__ == "__main__":
    # clean_old_files()
    run_pipeline()