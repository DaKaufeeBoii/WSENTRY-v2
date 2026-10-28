"""
Phase 2 runner v3: native features for same-dataset, behavioral for cross-dataset.
"""
import sys, os, json, time
import numpy as np
import torch
sys.path.insert(0, os.path.dirname(__file__))

from sklearn.metrics import accuracy_score, f1_score
from src.data.dataset_loader import (
    load_wsn, load_cic, load_edge, FEATURE_COLS, EDGE_NATIVE_COLS, get_feature_cols
)
from src.features.preprocessor import preprocess
from src.models.hybrid_dl import train_hybrid, predict_hybrid
from src.models.dann import train_dann, predict_dann
from src.models.calibration import fit_temperature, compute_ece, calibrated_predict
from src.eval.roc_export import export_roc
from src.utils import set_seed

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# Override with WSENTRY_SEED=<n> to repeat the whole run under a different seed
# (for mean/std reporting); 42 reproduces the published numbers.
SEED = int(os.environ.get("WSENTRY_SEED", "42"))
set_seed(SEED)
print(f"Device: {DEVICE}  Seed: {SEED}")


def eval_metrics(y_true, y_pred, name=""):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    return {"name": name, "accuracy": round(acc * 100, 2), "f1": round(f1 * 100, 2)}


# ---- Experiment 3a: Same-dataset with NATIVE features ----

def run_native_experiments():
    print("=" * 70)
    print("EXPERIMENT 3a: Hybrid DL — Native Features (Same-Dataset)")
    print("=" * 70)

    configs = {
        "WSN":  {"loader": load_wsn,  "mode": "native", "fcols": FEATURE_COLS},
        "CIC":  {"loader": load_cic,  "mode": "native", "fcols": FEATURE_COLS},
        "Edge": {"loader": load_edge, "mode": "native", "fcols": EDGE_NATIVE_COLS},
    }

    results = {}
    models = {}
    datasets = {}
    roc_data = {}

    for name, cfg in configs.items():
        print(f"\n--- {name} (n_features={len(cfg['fcols'])}) ---")
        df = cfg["loader"](mode=cfg["mode"])
        print(f"  Loaded: {len(df)} rows, classes: {dict(df['threat_class'].value_counts().sort_index())}")

        data = preprocess(df, feature_cols=cfg["fcols"], smote=False, time_steps=5,
                          random_state=SEED)
        datasets[name] = data
        n_feat = data["n_features"]

        # Remap to contiguous labels
        all_labels = np.concatenate([data["y_train_seq"], data["y_val_seq"], data["y_test_seq"]])
        classes = sorted(set(all_labels))
        lm = {c: i for i, c in enumerate(classes)}
        im = {i: c for c, i in lm.items()}
        n_cls = len(classes)

        y_tr = np.array([lm[y] for y in data["y_train_seq"]])
        y_va = np.array([lm[y] for y in data["y_val_seq"]])

        model, hist = train_hybrid(
            data["X_train_seq"], y_tr, data["X_val_seq"], y_va,
            n_features=n_feat, n_classes=n_cls,
            epochs=20, batch_size=256, device=DEVICE, seed=SEED
        )
        models[name] = (model, lm, im, n_cls, n_feat)

        preds, probs = predict_hybrid(model, data["X_test_seq"], device=DEVICE)
        preds_orig = np.array([im[p] for p in preds])
        m = eval_metrics(data["y_test_seq"], preds_orig, f"Native_{name}")
        results[name] = m
        # Retain probabilities so a true threshold-swept ROC can be computed.
        # y_true is remapped into the model's contiguous label space so it lines
        # up with the probability columns; classes[i] is the original class id.
        roc_data[name] = {
            "y_true": np.array([lm[y] for y in data["y_test_seq"]]),
            "probs": probs,
            "classes": classes,
        }
        print(f"  => Acc={m['accuracy']}%, F1={m['f1']}%")

    return results, models, datasets, roc_data


# ---- Experiment 3b: Cross-dataset with BEHAVIORAL features ----

def run_behavioral_transfer():
    print(f"\n{'=' * 70}")
    print("EXPERIMENT 3b: Hybrid DL — Behavioral Features (Cross-Dataset)")
    print("=" * 70)

    loaders = {"WSN": load_wsn, "CIC": load_cic, "Edge": load_edge}
    datasets = {}
    models = {}

    for name, loader in loaders.items():
        print(f"\n--- {name} (behavioral, 20 features) ---")
        df = loader(mode="behavioral")
        data = preprocess(df, feature_cols=FEATURE_COLS, smote=False, time_steps=5,
                          random_state=SEED)
        datasets[name] = data

        all_labels = np.concatenate([data["y_train_seq"], data["y_val_seq"], data["y_test_seq"]])
        classes = sorted(set(all_labels))
        lm = {c: i for i, c in enumerate(classes)}
        im = {i: c for c, i in lm.items()}
        n_cls = len(classes)

        y_tr = np.array([lm[y] for y in data["y_train_seq"]])
        y_va = np.array([lm[y] for y in data["y_val_seq"]])

        model, hist = train_hybrid(
            data["X_train_seq"], y_tr, data["X_val_seq"], y_va,
            n_features=20, n_classes=n_cls,
            epochs=20, batch_size=256, device=DEVICE, seed=SEED
        )
        models[name] = (model, lm, im, n_cls)

    # Transfer matrix
    print(f"\n{'Transfer Matrix':=^70}")
    transfer = {}
    names = list(loaders.keys())
    for train_n in names:
        for test_n in names:
            model, train_lm, train_im, n_cls = models[train_n]
            data_test = datasets[test_n]

            common = set(train_lm.keys()) & set(data_test["y_test_seq"])
            if not common:
                transfer[f"{train_n}→{test_n}"] = 0.0
                print(f"  {train_n}→{test_n}: No common classes")
                continue

            mask = np.isin(data_test["y_test_seq"], list(common))
            X_sub = data_test["X_test_seq"][mask]
            y_sub = data_test["y_test_seq"][mask]

            preds, _ = predict_hybrid(model, X_sub, device=DEVICE)
            preds_orig = np.array([train_im.get(p, -1) for p in preds])
            acc = round(accuracy_score(y_sub, preds_orig) * 100, 2)
            transfer[f"{train_n}→{test_n}"] = acc
            diag = "SAME" if train_n == test_n else "CROSS"
            print(f"  [{diag}] {train_n}→{test_n}: Acc={acc}%")

    # Table
    print(f"\n{'':>15}", "  ".join(f"{n:>8}" for n in names))
    for tn in names:
        row = f"  Train {tn:>8}"
        for te in names:
            row += f"{transfer[f'{tn}→{te}']:>8.1f}"
        print(row)

    return transfer, datasets, models


# ---- Experiment 4: DANN on CIC+Edge (2-domain) ----

def run_dann_2domain(datasets):
    print(f"\n{'=' * 70}")
    print("EXPERIMENT 4: DANN 2-Domain (CIC + Edge, behavioral features)")
    print("=" * 70)

    domain_map = {"CIC": 0, "Edge": 1}
    X_tr, y_tr, d_tr = [], [], []
    X_va, y_va, d_va = [], [], []

    all_classes = set()
    for name in ["CIC", "Edge"]:
        all_classes.update(set(datasets[name]["y_train_seq"]))
    classes = sorted(all_classes)
    lm = {c: i for i, c in enumerate(classes)}
    im = {i: c for c, i in lm.items()}
    n_cls = len(classes)

    for name in ["CIC", "Edge"]:
        data = datasets[name]
        d_id = domain_map[name]
        X_tr.append(data["X_train_seq"])
        y_tr.append(np.array([lm[y] for y in data["y_train_seq"]]))
        d_tr.append(np.full(len(data["y_train_seq"]), d_id))
        X_va.append(data["X_val_seq"])
        y_va.append(np.array([lm[y] for y in data["y_val_seq"]]))
        d_va.append(np.full(len(data["y_val_seq"]), d_id))

    X_train = np.concatenate(X_tr)
    y_train = np.concatenate(y_tr)
    d_train = np.concatenate(d_tr)
    X_val = np.concatenate(X_va)
    y_val = np.concatenate(y_va)
    d_val = np.concatenate(d_va)

    idx = np.random.RandomState(SEED).permutation(len(y_train))
    X_train, y_train, d_train = X_train[idx], y_train[idx], d_train[idx]

    print(f"  Pooled: train={len(y_train)}, val={len(y_val)}, classes={n_cls}")

    model, hist = train_dann(
        X_train, y_train, d_train, X_val, y_val, d_val,
        n_features=20, n_classes=n_cls, n_domains=2,
        epochs=25, batch_size=256, lambda_domain=0.1, pretrain_epochs=8,
        device=DEVICE, seed=SEED
    )

    results = {}
    for name in ["CIC", "Edge"]:
        data = datasets[name]
        preds, _ = predict_dann(model, data["X_test_seq"], device=DEVICE)
        preds_orig = np.array([im[p] for p in preds])
        m = eval_metrics(data["y_test_seq"], preds_orig, f"DANN2D_{name}")
        results[name] = m
        print(f"  {name}: Acc={m['accuracy']}%, F1={m['f1']}%")

    return results


# ---- Experiment 4b: DANN on WSN+CIC+Edge (3-domain) ----

def run_dann_3domain(datasets):
    """
    3-domain DANN (WSN + CIC + Edge). Reported in the paper as a negative
    result: routing-layer and transport-layer features share no structure, so
    no domain-invariant representation exists for the discriminator to find.
    Kept runnable so that claim is reproducible from the repo.
    """
    print(f"\n{'=' * 70}")
    print("EXPERIMENT 4b: DANN 3-Domain (WSN + CIC + Edge, behavioral features)")
    print("=" * 70)

    names = ["WSN", "CIC", "Edge"]
    domain_map = {n: i for i, n in enumerate(names)}

    all_classes = set()
    for n in names:
        all_classes.update(set(datasets[n]["y_train_seq"]))
    classes = sorted(all_classes)
    lm = {c: i for i, c in enumerate(classes)}
    im = {i: c for c, i in lm.items()}
    n_cls = len(classes)

    X_tr, y_tr, d_tr = [], [], []
    X_va, y_va, d_va = [], [], []
    for n in names:
        data = datasets[n]
        d_id = domain_map[n]
        X_tr.append(data["X_train_seq"])
        y_tr.append(np.array([lm[y] for y in data["y_train_seq"]]))
        d_tr.append(np.full(len(data["y_train_seq"]), d_id))
        X_va.append(data["X_val_seq"])
        y_va.append(np.array([lm[y] for y in data["y_val_seq"]]))
        d_va.append(np.full(len(data["y_val_seq"]), d_id))

    X_train = np.concatenate(X_tr)
    y_train = np.concatenate(y_tr)
    d_train = np.concatenate(d_tr)
    X_val = np.concatenate(X_va)
    y_val = np.concatenate(y_va)
    d_val = np.concatenate(d_va)

    idx = np.random.RandomState(SEED).permutation(len(y_train))
    X_train, y_train, d_train = X_train[idx], y_train[idx], d_train[idx]

    print(f"  Pooled: train={len(y_train)}, val={len(y_val)}, classes={n_cls}, domains=3")

    model, hist = train_dann(
        X_train, y_train, d_train, X_val, y_val, d_val,
        n_features=20, n_classes=n_cls, n_domains=3,
        epochs=25, batch_size=256, lambda_domain=0.1, pretrain_epochs=8,
        device=DEVICE, seed=SEED
    )

    results = {}
    for n in names:
        data = datasets[n]
        preds, _ = predict_dann(model, data["X_test_seq"], device=DEVICE)
        preds_orig = np.array([im[p] for p in preds])
        m = eval_metrics(data["y_test_seq"], preds_orig, f"DANN3D_{n}")
        results[n] = m
        print(f"  {n}: Acc={m['accuracy']}%, F1={m['f1']}%")

    # Convergence trace is the evidence for the negative result.
    t_acc = hist["val_threat_acc"]
    d_acc = hist["val_domain_acc"]
    results["convergence"] = {
        "final_threat_acc": round(t_acc[-1] * 100, 2) if t_acc else None,
        "best_threat_acc": round(max(t_acc) * 100, 2) if t_acc else None,
        "domain_acc_min": round(min(d_acc) * 100, 2) if d_acc else None,
        "domain_acc_max": round(max(d_acc) * 100, 2) if d_acc else None,
        "epochs_run": len(t_acc),
        "note": "Chance domain accuracy is 33.3% for 3 domains.",
    }
    c = results["convergence"]
    print(f"  Convergence: threat_acc final={c['final_threat_acc']}% "
          f"(best {c['best_threat_acc']}%), domain_acc range "
          f"{c['domain_acc_min']}-{c['domain_acc_max']}% over {c['epochs_run']} epochs")

    return results


# ---- Experiment 5: Calibration on native models ----

def run_calibration(models_dict, datasets_dict):
    print(f"\n{'=' * 70}")
    print("EXPERIMENT 5: Temperature Scaling")
    print("=" * 70)

    results = {}
    for name in models_dict:
        model, lm, im, n_cls, n_feat = models_dict[name]
        data = datasets_dict[name]
        y_val = np.array([lm[y] for y in data["y_val_seq"]])
        y_test = np.array([lm[y] for y in data["y_test_seq"]])

        _, probs_raw = predict_hybrid(model, data["X_test_seq"], device=DEVICE)
        ece_before = compute_ece(probs_raw, y_test)

        temp_scaler = fit_temperature(model, data["X_val_seq"], y_val, device=DEVICE)
        t_val = temp_scaler.temperature.item()

        _, probs_cal = calibrated_predict(model, temp_scaler, data["X_test_seq"], device=DEVICE)
        ece_after = compute_ece(probs_cal, y_test)

        results[name] = {
            "temperature": round(t_val, 3),
            "ece_before": round(ece_before * 100, 2),
            "ece_after": round(ece_after * 100, 2),
        }
        print(f"  {name}: T={t_val:.3f}, ECE: {ece_before*100:.2f}% → {ece_after*100:.2f}%")

    return results


if __name__ == "__main__":
    os.makedirs("data/processed", exist_ok=True)

    native_results, native_models, native_datasets, roc_data = run_native_experiments()
    transfer, beh_datasets, beh_models = run_behavioral_transfer()
    dann2d = run_dann_2domain(beh_datasets)

    # The 3-domain run roughly doubles DANN training time; set
    # WSENTRY_SKIP_3DOMAIN=1 to leave it out of a quick re-run.
    if os.environ.get("WSENTRY_SKIP_3DOMAIN") == "1":
        print("\n[skipped] DANN 3-domain (WSENTRY_SKIP_3DOMAIN=1)")
        dann3d = None
    else:
        dann3d = run_dann_3domain(beh_datasets)

    cal = run_calibration(native_models, native_datasets)

    print(f"\n{'=' * 70}")
    print("Exporting ROC curves (threshold-swept, one-vs-rest)")
    print("=" * 70)
    roc_summary = export_roc(
        roc_data,
        npz_path="data/processed/roc_curves.npz",
        json_path="data/processed/roc_curves.json",
    )

    output = {
        "seed": SEED,
        "native_same_dataset": native_results,
        "behavioral_transfer_matrix": transfer,
        "dann_2domain": dann2d,
        "dann_3domain": dann3d,
        "calibration": cal,
        "roc_auc": {
            k: {"macro_auc": v["macro_auc"], "micro_auc": v["micro_auc"]}
            for k, v in roc_summary.items()
        },
    }
    with open("data/processed/phase2_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to data/processed/phase2_results.json")
