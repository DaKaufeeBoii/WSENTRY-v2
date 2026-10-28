"""Shared helpers."""
import os
import random

import numpy as np


def set_seed(seed: int = 42) -> None:
    """
    Seed Python, NumPy and PyTorch RNGs so a training run is reproducible.

    Call this before constructing a model — weight initialization draws from the
    torch RNG, so seeding afterwards leaves the init non-deterministic.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
    except ImportError:  # helper stays usable without torch installed
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
