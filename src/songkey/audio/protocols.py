from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from songkey.audio.models import CapturedAudio


class AudioCapture(Protocol):
    def capture(self, seconds: float, is_interrupted: Callable[[], bool] | None = None) -> CapturedAudio:
        """Blocking capture of `seconds` of system-output audio, checked
        against `is_interrupted` between chunks for clean shutdown. Raises
        AppError on failure."""
        ...
