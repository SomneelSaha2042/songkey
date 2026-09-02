from __future__ import annotations

from typing import Protocol

from songkey.recognition.models import Track


class RecognitionProvider(Protocol):
    async def recognize(self, wav_bytes: bytes) -> Track | None:
        """Recognize a WAV clip. Returns None on no match. Raises AppError on failure."""
        ...
