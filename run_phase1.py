"""
Phase 1 runner: train baselines per-dataset + 3x3 transfer matrix.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from src.data.dataset_loader import load_wsn, load_cic, load_edge, FEATURE_COLS, THREAT_MAP
from src.features.preprocessor import preprocess
from src.models.baseline_ml import train_rf, train_xgb, evaluate


def run_same_dataset():
    """Train and test on same dataset -- the standard per-dataset metrics."""
    print("=" * 70)
    print("EXPERIMENT 1: Same-Dataset Performance")
    print("=" * 70)

    loaders = {
        "WSN-DS": load_wsn,
        "CIC-IoT": load_cic,
        "Edge-IIoT": load_edge,
    }

    results = {}
    for name, loader in loaders.items():
        print(f"\n--- {name} ---")
        df = loader()
        print(f"  Loaded: {len(df)} rows, classes: {dict(df['threat_class'].value_counts().sort_index())}")

        data = preprocess(df, smote=True, time_steps=5)
        print(f"  Train: {len(data['y_train'])}, Val: {len(data['y_val'])}, Test: {len(data['y_test'])}")

        for model_name, trainer in [("RF", train_rf), ("XGB", train_xgb)]:
            t0 = time.time()
            model = trainer(data["X_train"], data["y_train"])
            train_time = time.time() - t0

            t0 = time.time()
            metrics = evaluate(model, data["X_test"], data["y_test"], f"{model_name}_{name}")
            infer_time = time.time() - t0

            metrics["train_time_s"] = round(train_time, 2)
            metrics["inference_time_s"] = round(infer_time, 4)
            results[f"{model_name}_{name}"] = metrics

            print(f"  {model_name}: Acc={metrics['accuracy']}%, F1={metrics['f1']}%, "
                  f"FAR={metrics['far']}%, train={train_time:.1f}s")

    return results


def run_transfer_matrix():
    """Train on dataset A, test on dataset B for all 9 combinations."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Cross-Dataset Transfer Matrix (RF)")
    print("=" * 70)

    loaders = {
        "WSN": load_wsn,
        "CIC": load_cic,
        "Edge": load_edge,
    }

    datasets = {}
    for name, loader in loaders.items():
        df = loader()
        data = preprocess(df, smote=True, time_steps=5)
        datasets[name] = data

    matrix = {}
    for train_name in datasets:
        for test_name in datasets:
            data_train = datasets[train_name]
            data_test = datasets[test_name]

            model = train_rf(data_train["X_train"], data_train["y_train"])
            metrics = evaluate(model, data_test["X_test"], data_test["y_test"],
                             f"RF_train={train_name}_test={test_name}")

            key = f"{train_name}→{test_name}"
            matrix[key] = metrics["accuracy"]
            diag = "SAME" if train_name == test_name else "CROSS"
            print(f"  [{diag}] Train={train_name}, Test={test_name}: "
                  f"Acc={metrics['accuracy']}%, F1={metrics['f1']}%")

    # Print as table
    names = list(loaders.keys())
    print(f"\n{'Transfer Matrix (Accuracy %)':<30}", end="")
    print("  ".join(f"{n:>8}" for n in names))
    print("-" * 60)
    for train_n in names:
        row = f"  Train: {train_n:<20}"
        for test_n in names:
            row += f"{matrix[f'{train_n}→{test_n}']:>8.1f}"
        print(row)

    return matrix


if __name__ == "__main__":
    os.makedirs("data/processed", exist_ok=True)

    same = run_same_dataset()
    transfer = run_transfer_matrix()

    # Save results
    # ponytail: confusion_matrix is ndarray, convert for JSON
    for v in same.values():
        v["confusion_matrix"] = v["confusion_matrix"].tolist()

    output = {"same_dataset": same, "transfer_matrix": transfer}
    with open("data/processed/phase1_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to data/processed/phase1_results.json")
