from __future__ import annotations

from typing import Protocol

from songkey.audio.models import CapturedAudio


class AudioCapture(Protocol):
    def capture(self, seconds: float) -> CapturedAudio:
        """Blocking capture of `seconds` of system-output audio. Raises AppError on failure."""
        ...
