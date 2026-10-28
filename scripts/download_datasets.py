# Download datasets script
import os
import subprocess
import sys

def download_datasets():
    """Download required datasets from Kaggle."""
    
    datasets = [
        ("ghulamali/wsn-ds", "data/raw/"),
        ("madhavmalhotra/iot-intrusion-dataset", "data/raw/"),
        ("mohamedamineferrag/edgeiiotset-cyber-security-dataset-of-iot-iiot", "data/raw/")
    ]
    
    # Check for Kaggle API credentials
    if not os.getenv("KAGGLE_USERNAME") or not os.getenv("KAGGLE_KEY"):
        print("ERROR: Kaggle API credentials not found.")
        print("Set KAGGLE_USERNAME and KAGGLE_KEY environment variables.")
        print("Get your API key from: https://www.kaggle.com/account")
        sys.exit(1)
    
    os.makedirs("data/raw", exist_ok=True)
    
    for dataset, path in datasets:
        print(f"\nDownloading {dataset}...")
        try:
            subprocess.run([
                "kaggle", "datasets", "download", "-d", dataset,
                "-p", path, "--unzip"
            ], check=True)
            print(f"✓ {dataset} downloaded successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to download {dataset}: {e}")
            sys.exit(1)
    
    print("\n✓ All datasets downloaded successfully")
    print("Next step: Run 'python run_phase1.py' to start baseline experiments")

if __name__ == "__main__":
    download_datasets()
