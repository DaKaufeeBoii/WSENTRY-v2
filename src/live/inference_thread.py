"""
Background inference thread integrating PacketBuffer, InferenceEngine, and MitigationEngine.
"""
import time
import threading
from typing import Optional
import numpy as np

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.inference import InferenceEngine
from src.live.mitigation import MitigationEngine
from src.data.dataset_loader import FEATURE_COLS


class InferenceThread(threading.Thread):
    """
    Asynchronous daemon thread continuously consuming unclassified packet records
    from the PacketBuffer, running batched model inference, updating records,
    and triggering automated mitigation rules on threats.
    """

    def __init__(
        self,
        buffer: PacketBuffer,
        engine: InferenceEngine,
        mitigation: MitigationEngine,
        poll_interval: float = 0.1,
        batch_size: int = 32,
        time_steps: int = 5,
    ) -> None:
        super().__init__(daemon=True)
        self.buffer = buffer
        self.engine = engine
        self.mitigation = mitigation
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.time_steps = time_steps
        self._stop_event = threading.Event()
        self.is_running = False

    def stop(self) -> None:
        self.is_running = False
        self._stop_event.set()

    def run(self) -> None:
        self.is_running = True
        while not self._stop_event.is_set():
            records = self.buffer.get_unclassified(limit=self.batch_size)
            if not records:
                time.sleep(self.poll_interval)
                continue

            batch_tensors = []
            valid_records = []

            for rec in records:
                raw = rec.raw_features
                if not raw:
                    # Mark as Normal if empty
                    self.buffer.update_record(rec, prediction=0, confidence=0.99, label="Normal")
                    continue

                # Prepare feature vector (20 features)
                vec = [float(raw.get(col, 0.0)) for col in FEATURE_COLS]
                # Replicate across time_steps to form (time_steps, 20)
                seq = np.tile(vec, (self.time_steps, 1)).astype(np.float32)
                # Log normalization and clip
                seq = np.sign(seq) * np.log1p(np.abs(seq))
                seq = np.clip(seq, -50.0, 50.0)
                batch_tensors.append(seq)
                valid_records.append(rec)

            if batch_tensors:
                batch_arr = np.array(batch_tensors, dtype=np.float32)
                predictions = self.engine.predict_batch(batch_arr)

                for rec, (pred_class, conf, label) in zip(valid_records, predictions):
                    self.buffer.update_record(rec, prediction=pred_class, confidence=conf, label=label)

                    # Trigger mitigation if threat
                    if pred_class > 0:
                        self.mitigation.respond(rec)

            # Periodic cleanup of expired firewall rules
            self.mitigation.cleanup_expired(max_age_seconds=300.0)
            time.sleep(self.poll_interval)

