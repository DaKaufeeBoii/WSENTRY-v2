"""
Upload W-SENTRY model weights to HuggingFace Hub.
Requires: huggingface_hub, HF_TOKEN environment variable
"""
from pathlib import Path
import os
import sys

try:
    from huggingface_hub import HfApi, create_repo, upload_file
except ImportError:
    print("ERROR: huggingface_hub not installed")
    print("Install with: pip install huggingface_hub")
    sys.exit(1)

def upload_to_huggingface():
    """Upload trained models to HuggingFace."""
    
    # Check for HF token
    token = os.getenv("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN environment variable not set")
        print("Get your token from: https://huggingface.co/settings/tokens")
        print("Set with: export HF_TOKEN=your_token_here")
        sys.exit(1)
    
    api = HfApi()
    repo_id = "Riteesh-2k6/w-sentry"
    
    print(f"Uploading to: https://huggingface.co/{repo_id}")
    
    # Create repo (fails silently if exists)
    try:
        create_repo(
            repo_id=repo_id,
            token=token,
            repo_type="model",
            exist_ok=True,
            private=False
        )
        print(f"✓ Repository created/verified: {repo_id}")
    except Exception as e:
        print(f"Note: {e}")
    
    models_dir = Path("models/weights")
    if not models_dir.exists():
        print(f"ERROR: {models_dir} not found")
        print("Run 'python scripts/save_weights.py' first")
        sys.exit(1)
    
    # Upload model files
    files_to_upload = [
        "hybrid_cnnbilstm_cic.pth",
        "dann_cic_edge.pth",
        "model_card.json"
    ]
    
    for filename in files_to_upload:
        filepath = models_dir / filename
        if not filepath.exists():
            print(f"✗ {filename} not found, skipping")
            continue
        
        print(f"\nUploading {filename} ({filepath.stat().st_size / 1e6:.2f} MB)...")
        try:
            upload_file(
                path_or_fileobj=str(filepath),
                path_in_repo=filename,
                repo_id=repo_id,
                token=token,
                commit_message=f"Add {filename}"
            )
            print(f"  ✓ {filename} uploaded")
        except Exception as e:
            print(f"  ✗ Upload failed: {e}")
    
    # Create README for HF model card
    readme_content = """---
license: mit
language:
- en
tags:
- intrusion-detection
- wireless-security
- domain-adaptation
- pytorch
- cnn-bilstm
datasets:
- WSN-DS
- CIC-IoT-2023
- Edge-IIoTset
metrics:
- accuracy
pipeline_tag: image-classification
---

# W-SENTRY: Cross-Domain Wireless Intrusion Detection

**Domain Adversarial Neural Networks for Multi-Dataset IDS**

## Model Description

W-SENTRY is a cross-domain wireless intrusion detection system trained on WSN-DS, CIC-IoT-2023, and Edge-IIoTset datasets. This repository contains:

1. **Hybrid CNN-BiLSTM-Attention** — Trained on CIC-IoT-2023 (97.8% accuracy)
2. **DANN 2-domain** — Domain adaptation between CIC + Edge (96.5% / 96.3%)

## Quick Start

```python
import torch
from w_sentry.models import HybridCNNBiLSTMAttention

# Load checkpoint
checkpoint = torch.load('hybrid_cnnbilstm_cic.pth')
model = HybridCNNBiLSTMAttention(input_dim=20, num_classes=5)
model.load_state_dict(checkpoint['model_state_dict'])

# Inference
model.eval()
with torch.no_grad():
    predictions = model(X_test)
```

## Performance

| Model | Dataset | Accuracy |
|-------|---------|----------|
| Hybrid | CIC-IoT-2023 | 97.8% |
| Hybrid | WSN-DS | 98.1% |
| Hybrid | Edge-IIoTset | 94.4% |
| DANN | CIC (transfer) | 96.5% |
| DANN | Edge (transfer) | 96.3% |

## Citation

```bibtex
@inproceedings{thiruveedhula2027wsentry,
  title={Cross-Domain Transferability of Deep Learning Intrusion Detection},
  author={Thiruveedhula, Riteesh and Goud, M. Vikas and Gafar, Shaik and Reddy, V. Sai Tarun},
  booktitle={IEEE CONECCT},
  year={2027}
}
```

## Repository

- GitHub: [Riteesh-2k6/w-sentry](https://github.com/Riteesh-2k6/w-sentry)
- Paper: See release v1.0.0

## License

MIT
"""
    
    readme_path = Path("README_HF.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    print("\nUploading README.md...")
    try:
        upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=repo_id,
            token=token,
            commit_message="Add model card"
        )
        print("  ✓ README.md uploaded")
    except Exception as e:
        print(f"  ✗ Upload failed: {e}")
    
    print(f"\n✓ Upload complete!")
    print(f"  View at: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    upload_to_huggingface()
