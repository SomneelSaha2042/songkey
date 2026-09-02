from __future__ import annotations

from dataclasses import dataclass

SAMPLE_WIDTH_BYTES = 2  # 16-bit signed PCM


@dataclass(frozen=True, slots=True)
class AudioFormat:
    sample_rate: int
    channels: int
    sample_width: int = SAMPLE_WIDTH_BYTES


@dataclass(frozen=True, slots=True)
class CaptureMetrics:
    peak: int
    rms: float
    normalized_rms: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class CapturedAudio:
    pcm: bytes
    format: AudioFormat
    metrics: CaptureMetrics
