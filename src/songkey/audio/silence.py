from __future__ import annotations

import numpy as np

from songkey.audio.models import AudioFormat, CaptureMetrics

# Conservative: real quiet music sits well above this. Validated by
# tests/unit/test_silence.py against zero/near-silence/sine-wave buffers.
SILENCE_NORMALIZED_RMS_THRESHOLD = 0.005
INT16_FULL_SCALE = 32768.0


def compute_metrics(pcm: bytes, audio_format: AudioFormat, duration_seconds: float) -> CaptureMetrics:
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size == 0:
        return CaptureMetrics(peak=0, rms=0.0, normalized_rms=0.0, duration_seconds=duration_seconds)

    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    return CaptureMetrics(
        peak=peak,
        rms=rms,
        normalized_rms=rms / INT16_FULL_SCALE,
        duration_seconds=duration_seconds,
    )


def is_silent(metrics: CaptureMetrics) -> bool:
    return metrics.peak == 0 or metrics.normalized_rms < SILENCE_NORMALIZED_RMS_THRESHOLD
