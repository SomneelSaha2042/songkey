from __future__ import annotations

import numpy as np

from songkey.audio.models import AudioFormat
from songkey.audio.silence import compute_metrics, is_silent

FORMAT = AudioFormat(sample_rate=48000, channels=1, sample_width=2)


def _pcm_from_samples(samples: np.ndarray) -> bytes:
    return samples.astype(np.int16).tobytes()


def test_zero_buffer_is_silent():
    pcm = _pcm_from_samples(np.zeros(48000, dtype=np.int16))

    metrics = compute_metrics(pcm, FORMAT, duration_seconds=1.0)

    assert metrics.peak == 0
    assert is_silent(metrics)


def test_near_silence_buffer_is_silent():
    rng = np.random.default_rng(0)
    samples = rng.integers(-50, 50, size=48000, dtype=np.int16)
    pcm = _pcm_from_samples(samples)

    metrics = compute_metrics(pcm, FORMAT, duration_seconds=1.0)

    assert is_silent(metrics)


def test_sine_wave_is_not_silent():
    t = np.linspace(0, 1, 48000, endpoint=False)
    samples = (5000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    pcm = _pcm_from_samples(samples)

    metrics = compute_metrics(pcm, FORMAT, duration_seconds=1.0)

    assert not is_silent(metrics)


def test_empty_pcm_is_silent():
    metrics = compute_metrics(b"", FORMAT, duration_seconds=0.0)

    assert is_silent(metrics)
