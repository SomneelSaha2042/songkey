from __future__ import annotations

import asyncio

from shazamio import Shazam

from songkey.app.errors import AppError, AppErrorCode
from songkey.recognition.models import Track
from songkey.recognition.parser import parse_shazam_response

RECOGNITION_TIMEOUT_SECONDS = 12.0


class ShazamRecognitionProvider:
    """RecognitionProvider adapter over ShazamIO. The only module allowed to
    import shazamio."""

    def __init__(self, timeout_seconds: float = RECOGNITION_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds
        self._shazam = Shazam()

    async def recognize(self, wav_bytes: bytes) -> Track | None:
        try:
            result = await asyncio.wait_for(self._shazam.recognize(wav_bytes), timeout=self._timeout_seconds)
        except TimeoutError as exc:
            raise AppError(AppErrorCode.RECOGNITION_TIMEOUT) from exc
        except OSError as exc:
            raise AppError(AppErrorCode.OFFLINE, str(exc)) from exc
        except Exception as exc:
            raise AppError(AppErrorCode.PROVIDER_RESPONSE_INVALID, str(exc)) from exc

        return parse_shazam_response(result)
