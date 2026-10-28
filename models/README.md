# W-SENTRY Model Weights

**Status:** Model training scripts are available. Pre-trained weights can be generated on-demand.

## Quick Start: Generate Weights

```bash
# Activate environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Train and save model checkpoints (~10-30 mins depending on GPU)
python scripts/save_weights.py

# Upload to HuggingFace (requires HF_TOKEN env var)
export HF_TOKEN=your_token_here
python scripts/upload_to_hf.py
```

## Pre-computed Results Available

Instead of distributing large model checkpoints, you can reproduce the exact results from the paper:

**Phase 1 Baselines:** `data/processed/phase1_results.json`
- Random Forest and XGBoost trained on all 3 datasets
- Same-dataset accuracy: 92-99.6%
- Cross-dataset transfer matrix: 0.2-67.6%

**Phase 2 Deep Learning:** `data/processed/phase2_results.json`
- Hybrid CNN-BiLSTM-Attention: 94-98% same-dataset
- Cross-dataset transfer: 61-86% (behavioral features)
- DANN 2-domain: 96.5% CIC / 96.3% Edge

## Reproduce Training

Run the complete training pipeline:

```bash
# Phase 1: Baseline ML (RF + XGBoost)
python run_phase1.py
# Output: data/processed/phase1_results.json
# Time: ~10-20 minutes

# Phase 2: Deep Learning (Hybrid + DANN)
python run_phase2.py
# Output: data/processed/phase2_results.json  
# Time: ~2-4 hours on RTX 3050, ~8-12 hours on CPU
```

## Model Architecture

### Hybrid CNN-BiLSTM-Attention

```python
from src.models.hybrid_dl import HybridCNNBiLSTMAttention

model = HybridCNNBiLSTMAttention(
    input_dim=20,      # 20 behavioral features
    num_classes=5      # Normal, DoS, Intrusion, Spoofing, Jamming
)

# Architecture:
# - Conv1D: 15→32→64 (kernel_size=3, BatchNorm + ReLU)
# - BiLSTM: 2 layers, 128 hidden units
# - Self-Attention: scaled dot-product
# - Dense: 256→128→5
```

### DANN (Domain Adversarial)

```python
from src.models.dann import WSENTRY_DANN

model = WSENTRY_DANN(
    input_dim=20,
    num_classes=5,
    num_domains=2      # CIC + Edge
)

# Components:
# - Feature Extractor: CNN-BiLSTM-Attention backbone (shared)
# - Threat Classifier: 5-class (Normal, DoS, Intrusion, Spoofing, Jamming)
# - Gradient Reversal Layer: -alpha * grad during backprop
# - Domain Discriminator: 2-class (CIC vs Edge)
```

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | None (CPU works) | NVIDIA RTX 3050+ (6GB VRAM) |
| RAM | 8GB | 16GB |
| Storage | 10GB | 20GB |
| Training Time | 8-12 hours (CPU) | 2-4 hours (GPU) |

## Key Training Parameters

```python
# From run_phase2.py
epochs = 20
batch_size = 256
learning_rate = 1e-3
optimizer = 'Adam'
early_stopping_patience = 7
lr_scheduler = 'ReduceLROnPlateau' (patience=3, factor=0.5)

# Class weights (capped to prevent minority overfitting)
class_weights = inverse_frequency  # Capped at [0.5, 5.0]

# DANN specific
dann_pretrain_epochs = 8  # Train threat classifier first (alpha=0)
alpha_schedule = lambda epoch: 2.0 / (1.0 + np.exp(-5.0 * epoch/max_epochs)) - 1.0
```

## Performance Summary

| Model | Dataset | Accuracy | Notes |
|-------|---------|----------|-------|
| Hybrid (native) | WSN-DS | 98.1% | 14 routing features |
| Hybrid (native) | CIC-IoT-2023 | 97.8% | 48 flow features |
| Hybrid (native) | Edge-IIoTset | 94.4% | 35 protocol features + log norm |
| Hybrid (behavioral) | WSN→Edge | 80.7% | vs 11.9% RF baseline (+68.8pp) |
| Hybrid (behavioral) | Edge→CIC | 61.8% | vs 67.6% RF baseline |
| DANN 2-domain | CIC | 96.5% | Unified cross-dataset model |
| DANN 2-domain | Edge | 96.3% | Unified cross-dataset model |

## Citation

If you use these models or reproduce the training, please cite:

```bibtex
@inproceedings{thiruveedhula2027wsentry,
  title={Cross-Domain Transferability of Deep Learning Intrusion Detection},
  author={Thiruveedhula, Riteesh and Goud, M. Vikas and Gafar, Shaik and Reddy, V. Sai Tarun},
  booktitle={IEEE CONECCT},
  year={2027}
}
```

## License

MIT — See [LICENSE](../LICENSE)

---

**Note:** Pre-trained checkpoint generation is available via `scripts/save_weights.py`. For research reproducibility, we recommend running the full training pipeline (`run_phase1.py` + `run_phase2.py`) to verify results match the paper.
