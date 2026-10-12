# W-SENTRY

**Cross-Domain Wireless Intrusion Detection System with Domain Adversarial Neural Networks**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0-EE4C2C.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Major Project (2026-27)** — KG Reddy College of Engineering & Technology, Hyderabad  
> *Team:* Riteesh Thiruveedhula, M. Vikas Goud, Shaik Gafar, V. Sai Tarun Reddy  
> *Guide:* Dr. [Faculty Name]

---

## Overview

W-SENTRY is an AI-powered wireless network intrusion detection system that achieves **state-of-the-art cross-dataset generalization** through:

1. **Two-track feature engineering** — native dataset-specific features for same-dataset accuracy, protocol-agnostic behavioral features for cross-dataset transfer
2. **Log normalization preprocessing** — handles billion-range protocol values (tcp.ack_raw, tcp.payload) that destroy gradient flow (+37.6 pp accuracy gain on Edge-IIoTset)
3. **Domain Adversarial Neural Network (DANN)** — gradient reversal training closes 85% of the cross-dataset accuracy gap
4. **Hybrid CNN-BiLSTM-Attention architecture** — temporal pattern recognition for sequential network traffic

### Key Results

| Metric | Value |
|--------|-------|
| **Same-Dataset Accuracy** | WSN-DS: 98.1% · CIC-IoT-2023: 97.8% · Edge-IIoTset: 94.4% |
| **Cross-Dataset Transfer** | WSN→Edge: 80.7% · Edge→CIC: 61.8% (vs 11.9% / 67.6% baseline RF) |
| **DANN 2-Domain (CIC+Edge)** | 96.5% CIC / 96.3% Edge (unified model) |
| **Training Speed** | ~3 min/epoch on RTX 3050 (6GB VRAM, 200K samples, batch 256) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                        │
│  WSN-DS (374K) · CIC-IoT-2023 (1.05M) · Edge-IIoTset (50K)         │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FEATURE EXTRACTION                                                  │
│  ┌──────────────────┐  ┌────────────────────┐  ┌─────────────────┐ │
│  │ Native Features  │  │ Behavioral Features│  │ Log Normalization│ │
│  │ (14-48 cols)     │  │ (20 common cols)   │  │ + RobustScaler  │ │
│  └──────────────────┘  └────────────────────┘  └─────────────────┘ │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DEEP LEARNING MODELS                                                │
│  ┌─────────────────────────────┐  ┌────────────────────────────────┐│
│  │ Hybrid CNN-BiLSTM-Attention │  │ DANN (Domain Adversarial)      ││
│  │ Conv1D(15→32→64) + BN       │  │ Feature Extractor (shared)     ││
│  │ BiLSTM(64→128, 2 layers)    │  │ Threat Classifier (5 classes)  ││
│  │ Self-Attention + Dense      │  │ Gradient Reversal Layer        ││
│  │ Output: 5 threat classes    │  │ Domain Discriminator (3 doms)  ││
│  └─────────────────────────────┘  └────────────────────────────────┘│
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DETECTION & MITIGATION                                              │
│  Threat Classification · Firewall Rules · Dashboard (Streamlit)     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites
- Python 3.11+
- CUDA 12.1+ (for GPU training; CPU fallback supported)
- Git
- 8GB RAM (16GB recommended for full dataset processing)

### Setup

```bash
git clone https://github.com/Riteesh-2k6/w-sentry.git
cd w-sentry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download datasets (requires Kaggle API key)
# Set KAGGLE_USERNAME and KAGGLE_KEY environment variables first
python scripts/download_datasets.py
```

---

## Usage

### Phase 1: Baseline ML Models (Random Forest / XGBoost)

```bash
python run_phase1.py
# Output: data/processed/phase1_results.json
# Metrics: per-dataset accuracy + 3×3 transfer matrix
```

### Phase 2: Deep Learning (Hybrid + DANN)

```bash
python run_phase2.py
# Output: data/processed/phase2_results.json
# Trains:
#   - Hybrid CNN-BiLSTM-Attention (native + behavioral features)
#   - DANN 3-domain (WSN+CIC+Edge) and 2-domain (CIC+Edge)
#   - Temperature scaling calibration
```

### Phase 3: Dashboard + Live Demo (TODO)

See `docs/PHASE3_PLAN.md` for implementation plan.

```bash
streamlit run src/dashboard/app.py
# Opens SOC dashboard at http://localhost:8501
# Tabs: Performance, Live Monitor, Transfer Matrix, ROC/AUC, Per-Class, Mitigation
```

---

## Project Structure

```
w-sentry/
├── data/
│   ├── raw/                      # Downloaded datasets (not in repo, use scripts/download_datasets.py)
│   │   ├── WSN-DS.csv            # 374K samples, 15 routing features
│   │   ├── IoT_Intrusion.csv     # CIC-IoT-2023, 1.05M samples, 48 flow features
│   │   └── ML-EdgeIIoT-dataset.csv  # 50K samples (balanced), 48 protocol features
│   └── processed/                # Experiment results (JSON)
│       ├── phase1_results.json   # RF/XGBoost baselines
│       └── phase2_results.json   # Hybrid DL + DANN results
├── src/
│   ├── data/
│   │   └── dataset_loader.py     # Two-track loader (native vs behavioral features)
│   ├── features/
│   │   └── preprocessor.py       # Log normalization + RobustScaler + SMOTE + windowing
│   ├── models/
│   │   ├── baseline_ml.py        # RandomForest + XGBoost
│   │   ├── hybrid_dl.py          # CNN-BiLSTM-Attention
│   │   ├── dann.py               # Domain Adversarial Neural Network
│   │   └── calibration.py        # Temperature scaling + ECE
│   ├── dashboard/                # Streamlit SOC interface (Phase 3)
│   ├── live/                     # Scapy capture + real-time inference (Phase 3)
│   ├── attack/                   # hping3/nmap/ARP spoof scripts (Phase 3)
│   └── mitigation/               # Firewall automation (Phase 3)
├── tests/                        # Pytest suite (11/11 passing)
│   ├── test_phase1.py
│   └── test_phase2.py
├── paper/                        # IEEE conference paper draft
│   ├── w-sentry-paper-draft.md
│   └── figures/
│       ├── fig1_architecture.html  # Interactive SVG architecture diagram
│       ├── fig2_transfer_matrix.png
│       ├── fig3_accuracy_comparison.png
│       └── fig4_log_normalization_ablation.png
├── docs/
│   ├── PHASE3_PLAN.md            # Dashboard implementation plan (700 lines, 9 task blocks)
│   └── ...
├── run_phase1.py                 # Phase 1 experiment runner
├── run_phase2.py                 # Phase 2 experiment runner
├── requirements.txt
└── README.md
```

---

## Research Contribution

**Novel contributions:**

1. **First 3×3 cross-dataset transfer study** on WSN-DS, CIC-IoT-2023, and Edge-IIoTset
2. **Log normalization preprocessing** for network traffic (solves billion-range protocol field problem)
3. **Two-track feature engineering** pattern for IDS (native + behavioral dual pipeline)
4. **DANN application to wireless IDS** — closes 85% of cross-dataset gap (vs 18.2% RF baseline)

**Target venues:**
- IEEE CONECCT 2027 (International Conference on Electronics, Computing and Communication Technologies)
- IEEE ICCCNT 2027 (International Conference on Computing, Communication and Networking Technologies)
- IEEE Access (journal, open access)

**Paper status:** Draft complete (2,860 words, 7 tables, 4 figures, 11 references)

---

## Datasets

| Dataset | Samples | Features | Attack Types | Domain |
|---------|---------|----------|--------------|--------|
| [WSN-DS](https://www.kaggle.com/datasets/ghulamali/wsn-ds) | 374K | 14 routing | Grayhole, Blackhole, Flooding, TDMA, Scheduling | Wireless Sensor Networks |
| [CIC-IoT-2023](https://www.kaggle.com/datasets/madhavmalhotra/iot-intrusion-dataset) | 1.05M | 48 flow | DDoS (HTTP/TCP/UDP), Recon, MITM, Spoofing, Backdoor | IoT Network Traffic |
| [Edge-IIoTset](https://www.kaggle.com/datasets/mohamedamineferrag/edgeiiotset-cyber-security-dataset-of-iot-iiot) | 50K (ML file) | 35 protocol | DDoS, SQL injection, XSS, Ransomware, Port scan, Backdoor | Industrial Edge Networks |

**License:** All datasets are publicly available under their respective licenses (citation required).

**Download script:** `scripts/download_datasets.py` (requires Kaggle API credentials)

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 |
| **RAM** | 8GB | 16GB |
| **GPU** | None (CPU training works) | NVIDIA RTX 3050+ (6GB VRAM) |
| **Storage** | 10GB | 20GB (datasets + models) |
| **OS** | Windows 10/11, Ubuntu 20.04+ | Windows 11 / Ubuntu 22.04 |

**Tested on:**
- Windows 11 with RTX 3050 (6GB), CUDA 13.0, PyTorch 2.6.0+cu128
- Training time: ~3 min/epoch (GPU) vs ~20 min/epoch (CPU) for 200K sequences

---

## Citation

If you use W-SENTRY in your research, please cite:

```bibtex
@inproceedings{thiruveedhula2027wsentry,
  title={Cross-Domain Transferability of Deep Learning Intrusion Detection: A Multi-Dataset Study with Domain Adversarial Training},
  author={Thiruveedhula, Riteesh and Goud, M. Vikas and Gafar, Shaik and Reddy, V. Sai Tarun},
  booktitle={IEEE International Conference on Electronics, Computing and Communication Technologies (CONECCT)},
  year={2027},
  organization={IEEE}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Base Papers:**
  - Phalaagae et al., "A Hybrid CNN-LSTM Model With Attention Mechanism for Improved Intrusion Detection in Wireless IoT Sensor Networks," *IEEE Access*, 2025
  - Ganin et al., "Domain-Adversarial Training of Neural Networks," *JMLR*, 2016
- **Datasets:** WSN-DS (Almomani et al.), CIC-IoT-2023 (Canadian Institute for Cybersecurity), Edge-IIoTset (Ferrag et al.)
- **Institution:** KG Reddy College of Engineering & Technology, Hyderabad

---

## Contact

- **Riteesh Thiruveedhula** — [triteesh@outlook.com](mailto:triteesh@outlook.com) | [LinkedIn](https://linkedin.com/in/riteesh2k6) | [GitHub](https://github.com/Riteesh-2k6)
- **Project Repository** — [https://github.com/Riteesh-2k6/w-sentry](https://github.com/Riteesh-2k6/w-sentry)

---

**Status:** ✅ Phase 1 Complete · ✅ Phase 2 Complete · 🚧 Phase 3 (Dashboard) In Progress · 📝 Phase 4 (Paper) Draft Ready
