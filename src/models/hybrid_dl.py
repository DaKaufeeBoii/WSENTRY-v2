"""
Hybrid CNN-BiLSTM-Self-Attention model for W-SENTRY.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

from src.utils import set_seed


class SelfAttention(nn.Module):
    """Scaled dot-product self-attention over temporal dimension."""
    def __init__(self, dim):
        super().__init__()
        self.q = nn.Linear(dim, dim)
        self.k = nn.Linear(dim, dim)
        self.v = nn.Linear(dim, dim)
        self.scale = dim ** 0.5

    def forward(self, x):
        # x: (batch, seq, dim)
        q, k, v = self.q(x), self.k(x), self.v(x)
        scores = torch.bmm(q, k.transpose(1, 2)) / self.scale
        attn = F.softmax(scores, dim=-1)
        return torch.bmm(attn, v)


class HybridCNNBiLSTMAttention(nn.Module):
    """
    Input: (batch, time_steps, n_features)
    Output: (batch, n_classes) logits
    """
    def __init__(self, n_features=15, n_classes=5, hidden_dim=128, dropout=0.3):
        super().__init__()
        # CNN: operates on (batch, channels, seq_len) → treat features as channels
        self.conv1 = nn.Conv1d(n_features, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(32)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(64)
        self.drop_cnn = nn.Dropout(0.2)

        # BiLSTM
        self.lstm = nn.LSTM(64, hidden_dim, num_layers=2, batch_first=True,
                           bidirectional=True, dropout=dropout)

        # Attention over BiLSTM output
        self.attention = SelfAttention(hidden_dim * 2)

        # Classifier
        self.fc1 = nn.Linear(hidden_dim * 2, hidden_dim)
        self.drop_fc = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_dim, n_classes)

    def forward(self, x):
        # x: (batch, time_steps, features)
        # CNN expects (batch, channels, seq_len)
        h = x.transpose(1, 2)
        h = self.drop_cnn(F.relu(self.bn1(self.conv1(h))))
        h = self.drop_cnn(F.relu(self.bn2(self.conv2(h))))

        # Back to (batch, seq, channels) for LSTM
        h = h.transpose(1, 2)
        h, _ = self.lstm(h)  # (batch, seq, hidden*2)

        # Self-attention
        h = self.attention(h)  # (batch, seq, hidden*2)

        # Mean pool over time
        h = h.mean(dim=1)  # (batch, hidden*2)

        # Classify
        h = self.drop_fc(F.relu(self.fc1(h)))
        return self.fc2(h)

    def extract_features(self, x):
        """Return the 256-dim representation before classifier. Used by DANN."""
        h = x.transpose(1, 2)
        h = self.drop_cnn(F.relu(self.bn1(self.conv1(h))))
        h = self.drop_cnn(F.relu(self.bn2(self.conv2(h))))
        h = h.transpose(1, 2)
        h, _ = self.lstm(h)
        h = self.attention(h)
        return h.mean(dim=1)


def train_hybrid(X_train, y_train, X_val, y_val, n_features=15, n_classes=5,
                 epochs=30, batch_size=256, lr=1e-3, device="cpu", seed=42):
    """Train the hybrid model with class-weighted loss. Returns (model, history)."""
    # Seed before constructing the model: weight init draws from the torch RNG.
    set_seed(seed)
    model = HybridCNNBiLSTMAttention(n_features, n_classes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    # Class weights: capped inverse frequency (softer than raw inverse)
    counts = np.bincount(y_train, minlength=n_classes).astype(np.float32)
    counts[counts == 0] = 1.0
    weights = (1.0 / counts) * len(y_train) / n_classes
    weights = np.clip(weights, 0.5, 5.0)  # ponytail: cap to avoid overcorrection
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights).to(device))

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train, dtype=torch.long))
    val_ds = TensorDataset(torch.tensor(X_val), torch.tensor(y_val, dtype=torch.long))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size)

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            out = model(xb)
            loss = criterion(out, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss, correct, total = 0, 0, 0
        with torch.no_grad():
            for xb, yb in val_dl:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                val_loss += criterion(out, yb).item() * len(xb)
                correct += (out.argmax(1) == yb).sum().item()
                total += len(yb)
        val_loss /= len(val_ds)
        val_acc = correct / total

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:>3d}: train_loss={train_loss:.4f} "
                  f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}")

        # ponytail: early stop at 7 epochs no improvement
        if patience_counter >= 7:
            print(f"  Early stop at epoch {epoch+1}")
            break

    model.load_state_dict(best_state)
    return model, history


def predict_hybrid(model, X_test, batch_size=512, device="cpu"):
    """Returns (predictions, probabilities)."""
    model.eval()
    ds = TensorDataset(torch.tensor(X_test))
    dl = DataLoader(ds, batch_size=batch_size)
    preds, probs = [], []
    with torch.no_grad():
        for (xb,) in dl:
            out = model(xb.to(device))
            p = F.softmax(out, dim=1)
            preds.append(out.argmax(1).cpu().numpy())
            probs.append(p.cpu().numpy())
    return np.concatenate(preds), np.concatenate(probs)
