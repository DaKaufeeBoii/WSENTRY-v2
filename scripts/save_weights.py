"""
Save trained W-SENTRY model weights for distribution.
Creates checkpoints for: Hybrid CNN-BiLSTM-Attention and DANN models.
"""
import torch
import json
from pathlib import Path
import sys
sys.path.append('.')

from src.data.dataset_loader import load_wsn, load_cic, load_edge
from src.features.preprocessor import preprocess
from src.models.hybrid_dl import HybridCNNBiLSTMAttention, train_hybrid
from src.models.dann import WSENTRY_DANN, train_dann

def save_model_weights():
    """Train and save model weights for distribution."""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    models_dir = Path("models/weights")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Load datasets (behavioral features for cross-dataset compatibility)
    print("\n[1/4] Loading datasets...")
    X_wsn, y_wsn = load_wsn(mode='behavioral')
    X_cic, y_cic = load_cic(mode='behavioral')
    X_edge, y_edge = load_edge(mode='behavioral')
    
    print(f"  WSN: {X_wsn.shape}, CIC: {X_cic.shape}, Edge: {X_edge.shape}")
    
    # Preprocess
    print("[2/4] Preprocessing...")
    import pandas as pd
    
    # Convert to DataFrames for preprocess function
    wsn_df = pd.DataFrame(X_wsn)
    wsn_df['label'] = y_wsn
    X_wsn_train, _, X_wsn_val, _, y_wsn_train, _, y_wsn_val, _, scaler = preprocess(
        wsn_df, test_size=0.2, val_size=0.1, smote=False
    )
    X_wsn = np.vstack([X_wsn_train, X_wsn_val])
    y_wsn = np.hstack([y_wsn_train, y_wsn_val])
    
    cic_df = pd.DataFrame(X_cic)
    cic_df['label'] = y_cic
    X_cic_train, _, X_cic_val, _, y_cic_train, _, y_cic_val, _, _ = preprocess(
        cic_df, test_size=0.2, val_size=0.1, smote=False, scaler=scaler
    )
    X_cic = np.vstack([X_cic_train, X_cic_val])
    y_cic = np.hstack([y_cic_train, y_cic_val])
    
    edge_df = pd.DataFrame(X_edge)
    edge_df['label'] = y_edge
    X_edge_train, _, X_edge_val, _, y_edge_train, _, y_edge_val, _, _ = preprocess(
        edge_df, test_size=0.2, val_size=0.1, smote=False, scaler=scaler
    )
    X_edge = np.vstack([X_edge_train, X_edge_val])
    y_edge = np.hstack([y_edge_train, y_edge_val])
    
    # Train Hybrid model on CIC (best cross-dataset performance)
    print("\n[3/4] Training Hybrid CNN-BiLSTM-Attention (CIC-IoT-2023)...")
    input_dim = X_cic.shape[2]
    hybrid_model = HybridCNNBiLSTMAttention(input_dim=input_dim, num_classes=5).to(device)
    
    hybrid_model, train_acc, val_acc = train_hybrid(
        hybrid_model, X_cic, y_cic, 
        epochs=10,  # Quick training for weights
        batch_size=256,
        device=device
    )
    
    # Save Hybrid checkpoint
    hybrid_checkpoint = {
        'model_state_dict': hybrid_model.state_dict(),
        'input_dim': input_dim,
        'num_classes': 5,
        'train_accuracy': train_acc,
        'val_accuracy': val_acc,
        'dataset': 'CIC-IoT-2023',
        'feature_mode': 'behavioral',
        'architecture': 'CNN-BiLSTM-Attention',
        'description': 'Trained on CIC-IoT-2023 behavioral features (20 columns) for cross-dataset transfer'
    }
    
    hybrid_path = models_dir / "hybrid_cnnbilstm_cic.pth"
    torch.save(hybrid_checkpoint, hybrid_path)
    print(f"  ✓ Saved: {hybrid_path} ({hybrid_path.stat().st_size / 1e6:.2f} MB)")
    print(f"    Train: {train_acc:.2f}%, Val: {val_acc:.2f}%")
    
    # Train DANN 2-domain (CIC + Edge)
    print("\n[4/4] Training DANN 2-domain (CIC + Edge)...")
    dann_model = WSENTRY_DANN(input_dim=input_dim, num_classes=5, num_domains=2).to(device)
    
    # Combine datasets
    import numpy as np
    X_combined = np.vstack([X_cic, X_edge])
    y_combined = np.hstack([y_cic, y_edge])
    domain_labels = np.hstack([
        np.zeros(len(y_cic)),  # CIC = domain 0
        np.ones(len(y_edge))   # Edge = domain 1
    ])
    
    dann_model, train_acc, val_acc = train_dann(
        dann_model, X_combined, y_combined, domain_labels,
        epochs=10,
        batch_size=256,
        device=device
    )
    
    # Save DANN checkpoint
    dann_checkpoint = {
        'model_state_dict': dann_model.state_dict(),
        'input_dim': input_dim,
        'num_classes': 5,
        'num_domains': 2,
        'train_accuracy': train_acc,
        'val_accuracy': val_acc,
        'datasets': ['CIC-IoT-2023', 'Edge-IIoTset'],
        'feature_mode': 'behavioral',
        'architecture': 'DANN (Domain Adversarial)',
        'description': 'Domain adaptation between CIC and Edge networks via gradient reversal'
    }
    
    dann_path = models_dir / "dann_cic_edge.pth"
    torch.save(dann_checkpoint, dann_path)
    print(f"  ✓ Saved: {dann_path} ({dann_path.stat().st_size / 1e6:.2f} MB)")
    print(f"    Train: {train_acc:.2f}%, Val: {val_acc:.2f}%")
    
    # Save metadata
    metadata = {
        "models": {
            "hybrid_cnnbilstm_cic.pth": {
                "architecture": "CNN-BiLSTM-Attention",
                "dataset": "CIC-IoT-2023",
                "accuracy": f"{val_acc:.2f}%",
                "parameters": sum(p.numel() for p in hybrid_model.parameters()),
                "size_mb": round(hybrid_path.stat().st_size / 1e6, 2)
            },
            "dann_cic_edge.pth": {
                "architecture": "DANN (2-domain)",
                "datasets": ["CIC-IoT-2023", "Edge-IIoTset"],
                "accuracy": f"{val_acc:.2f}%",
                "parameters": sum(p.numel() for p in dann_model.parameters()),
                "size_mb": round(dann_path.stat().st_size / 1e6, 2)
            }
        },
        "feature_configuration": {
            "mode": "behavioral",
            "features": 20,
            "sequence_length": 5,
            "preprocessing": "log_normalization + RobustScaler"
        },
        "usage": {
            "load_example": "checkpoint = torch.load('hybrid_cnnbilstm_cic.pth'); model.load_state_dict(checkpoint['model_state_dict'])",
            "inference": "See inference_example.py"
        }
    }
    
    with open(models_dir / "model_card.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("\n✓ Model weights saved successfully!")
    print(f"  Location: {models_dir.absolute()}")
    print(f"  Files: hybrid_cnnbilstm_cic.pth, dann_cic_edge.pth, model_card.json")
    print("\nNext: Upload to HuggingFace with 'python scripts/upload_to_hf.py'")

if __name__ == "__main__":
    save_model_weights()
