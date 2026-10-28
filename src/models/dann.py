"""
DANN: Domain Adversarial Neural Network for cross-dataset transfer.
Gradient reversal forces the feature extractor to learn dataset-invariant representations.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

from src.models.hybrid_dl import HybridCNNBiLSTMAttention, SelfAttention
from src.utils import set_seed


class GradientReversal(torch.autograd.Function):
    """Flips gradient sign during backprop."""
    @staticmethod
    def forward(ctx, x, alpha):
        ctx.alpha = alpha
        return x.clone()

    @staticmethod
    def backward(ctx, grad_output):
        return -ctx.alpha * grad_output, None


class DANN(nn.Module):
    """
    Domain Adversarial Neural Network.
    Shared feature extractor + threat classifier + domain discriminator.
    """
    def __init__(self, n_features=15, n_classes=5, n_domains=3, hidden_dim=128, dropout=0.3):
        super().__init__()
        self.feature_extractor = HybridCNNBiLSTMAttention(n_features, n_classes, hidden_dim, dropout)
        feat_dim = hidden_dim * 2  # BiLSTM doubles

        # Threat classifier (replaces the original fc1+fc2)
        self.threat_classifier = nn.Sequential(
            nn.Linear(feat_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, n_classes),
        )

        # Domain discriminator
        self.domain_classifier = nn.Sequential(
            nn.Linear(feat_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, n_domains),
        )

    def forward(self, x, alpha=1.0):
        features = self.feature_extractor.extract_features(x)
        threat_out = self.threat_classifier(features)
        reversed_features = GradientReversal.apply(features, alpha)
        domain_out = self.domain_classifier(reversed_features)
        return threat_out, domain_out

    def predict(self, x):
        """Threat prediction only."""
        features = self.feature_extractor.extract_features(x)
        return self.threat_classifier(features)


def _alpha_schedule(epoch, max_epochs):
    """Slower ramp: alpha reaches ~0.5 at midpoint, ~0.9 at end."""
    p = epoch / max_epochs
    return 2.0 / (1.0 + np.exp(-5.0 * p)) - 1.0  # was -10.0, now -5.0


def train_dann(X_train, y_train, d_train, X_val, y_val, d_val,
               n_features=15, n_classes=5, n_domains=3,
               epochs=30, batch_size=256, lr=1e-3, lambda_domain=1.0,
               pretrain_epochs=5, device="cpu", seed=42):
    """
    Train DANN with pre-training phase.
    First trains threat classifier only, then enables gradient reversal.
    """
    # Seed before constructing the model: weight init draws from the torch RNG.
    set_seed(seed)
    model = DANN(n_features, n_classes, n_domains).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)
    # Class-weighted threat loss (capped)
    counts = np.bincount(y_train, minlength=n_classes).astype(np.float32)
    counts[counts == 0] = 1.0
    t_weights = (1.0 / counts) * len(y_train) / n_classes
    t_weights = np.clip(t_weights, 0.5, 5.0)
    threat_criterion = nn.CrossEntropyLoss(weight=torch.tensor(t_weights).to(device))
    domain_criterion = nn.CrossEntropyLoss()

    train_ds = TensorDataset(
        torch.tensor(X_train), torch.tensor(y_train, dtype=torch.long),
        torch.tensor(d_train, dtype=torch.long)
    )
    val_ds = TensorDataset(
        torch.tensor(X_val), torch.tensor(y_val, dtype=torch.long),
        torch.tensor(d_val, dtype=torch.long)
    )
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size)

    history = {"train_loss": [], "val_loss": [], "val_threat_acc": [], "val_domain_acc": []}
    best_val_loss = float("inf")
    patience_counter = 0
    total_epochs = pretrain_epochs + epochs

    for epoch in range(total_epochs):
        # Phase 1: pretrain (no gradient reversal)
        # Phase 2: DANN with ramping alpha
        if epoch < pretrain_epochs:
            alpha = 0.0
            use_domain = False
        else:
            alpha = _alpha_schedule(epoch - pretrain_epochs, epochs)
            use_domain = True

        # Train
        model.train()
        total_loss = 0
        for xb, yb, db in train_dl:
            xb, yb, db = xb.to(device), yb.to(device), db.to(device)
            threat_out, domain_out = model(xb, alpha)
            loss_t = threat_criterion(threat_out, yb)
            if use_domain:
                loss_d = domain_criterion(domain_out, db)
                loss = loss_t + lambda_domain * loss_d
            else:
                loss = loss_t
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(xb)
        total_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss, t_correct, d_correct, total = 0, 0, 0, 0
        with torch.no_grad():
            for xb, yb, db in val_dl:
                xb, yb, db = xb.to(device), yb.to(device), db.to(device)
                threat_out, domain_out = model(xb, alpha)
                loss_t = threat_criterion(threat_out, yb)
                loss_d = domain_criterion(domain_out, db)
                val_loss += (loss_t + lambda_domain * loss_d).item() * len(xb)
                t_correct += (threat_out.argmax(1) == yb).sum().item()
                d_correct += (domain_out.argmax(1) == db).sum().item()
                total += len(yb)
        val_loss /= len(val_ds)
        t_acc = t_correct / total
        d_acc = d_correct / total

        scheduler.step(val_loss)
        history["train_loss"].append(total_loss)
        history["val_loss"].append(val_loss)
        history["val_threat_acc"].append(t_acc)
        history["val_domain_acc"].append(d_acc)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:>3d}: loss={total_loss:.4f} val_loss={val_loss:.4f} "
                  f"threat_acc={t_acc:.4f} domain_acc={d_acc:.4f} alpha={alpha:.3f}")

        if patience_counter >= 7:
            print(f"  Early stop at epoch {epoch+1}")
            break

    model.load_state_dict(best_state)
    return model, history


def predict_dann(model, X_test, batch_size=512, device="cpu"):
    """Returns (predictions, probabilities) for threat classification."""
    model.eval()
    ds = TensorDataset(torch.tensor(X_test))
    dl = DataLoader(ds, batch_size=batch_size)
    preds, probs = [], []
    with torch.no_grad():
        for (xb,) in dl:
            out = model.predict(xb.to(device))
            p = F.softmax(out, dim=1)
            preds.append(out.argmax(1).cpu().numpy())
            probs.append(p.cpu().numpy())
    return np.concatenate(preds), np.concatenate(probs)
