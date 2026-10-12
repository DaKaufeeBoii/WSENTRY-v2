"""
Background daemon thread for real-time batched model inference and mitigation triggering.
"""
import logging
import threading
import time
from typing import List

import numpy as np

from src.data.dataset_loader import FEATURE_COLS
from src.live.buffer import PacketBuffer, PacketRecord
from src.live.inference import InferenceEngine
from src.live.mitigation import MitigationEngine

logger = logging.getLogger("w_sentry.inference_thread")


class InferenceThread(threading.Thread):
    """
    Background daemon thread that:
    1. Polls PacketBuffer for records with prediction == -1.
    2. Batches up to batch_size records for inference.
    3. Calls InferenceEngine.predict_batch().
    4. Updates records in-place with prediction, confidence, label.
    5. Dispatches threat records to MitigationEngine.respond().
    6. Sleeps poll_interval between loops.
    """

    def __init__(
        self,
        buffer: PacketBuffer,
        engine: InferenceEngine,
        mitigation: MitigationEngine,
        poll_interval: float = 0.1,
        batch_size: int = 32,
        scaler: Any = None,
    ) -> None:
        super().__init__(daemon=True, name="WSentryInferenceThread")
        self.buffer = buffer
        self.engine = engine
        self.mitigation = mitigation
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._running = False

        if scaler is None:
            from src.live.feature_extractor import LiveFeatureExtractor
            try:
                self.scaler = LiveFeatureExtractor().scaler
            except Exception:
                self.scaler = None
        else:
            self.scaler = scaler

    def start(self) -> None:
        self._running = True
        super().start()

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self._running = True
        logger.info("InferenceThread started.")

        while self._running:
            try:
                # Fetch pending unclassified records
                batch = self.buffer.get_unclassified(max_batch=self.batch_size)
                if not batch:
                    time.sleep(self.poll_interval)
                    continue

                # Prepare feature tensor of shape (batch_size, 5, 20)
                seq_list = []
                for rec in batch:
                    raw_vec = [rec.raw_features.get(col, 0.0) for col in FEATURE_COLS]
                    # Log-transform and clip matching pipeline
                    raw_arr = np.array(raw_vec, dtype=np.float32)
                    log_arr = np.sign(raw_arr) * np.log1p(np.abs(raw_arr))
                    clip_arr = np.clip(log_arr, -50.0, 50.0)

                    # Scale using real fitted RobustScaler
                    if self.scaler is not None:
                        scaled_arr = self.scaler.transform(clip_arr.reshape(1, -1))[0].astype(np.float32)
                    else:
                        scaled_arr = clip_arr.astype(np.float32)

                    # Tile across 5 time steps matching (batch, 5, 20)
                    seq = np.tile(scaled_arr, (5, 1))
                    seq_list.append(seq)

                features_batch = np.stack(seq_list, axis=0)
                predictions = self.engine.predict_batch(features_batch)

                # Update buffer records and trigger mitigation for threats
                for rec, (pred_cls, conf, label) in zip(batch, predictions):
                    self.buffer.update_prediction(rec, pred_cls, conf, label)
                    if pred_cls > 0:
                        self.mitigation.respond(rec)

            except Exception as e:
                logger.error(f"Inference error in background thread: {e}")
                time.sleep(self.poll_interval)

        logger.info("InferenceThread stopped.")
