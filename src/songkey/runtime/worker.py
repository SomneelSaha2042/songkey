from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, QThread, Signal, Slot

from songkey.app.errors import AppError, AppErrorCode
from songkey.audio.protocols import AudioCapture
from songkey.audio.silence import is_silent
from songkey.audio.wav import encode_wav
from songkey.recognition.models import Track
from songkey.recognition.protocols import RecognitionProvider

CAPTURE_SECONDS = 6.0


class RecognitionWorker(QObject):
    """Lives on a dedicated QThread. Depends only on the AudioCapture and
    RecognitionProvider protocols — concrete adapters are wired in
    bootstrap.py. Communicates back to the main thread exclusively through
    these signals (queued automatically by Qt across thread affinity)."""

    capture_complete = Signal(int)
    no_audio = Signal(int)
    found = Signal(int, object)  # Track
    not_found = Signal(int)
    failed = Signal(int, object)  # AppError

    def __init__(self, capture: AudioCapture, provider: RecognitionProvider, capture_seconds: float = CAPTURE_SECONDS) -> None:
        super().__init__()
        self._capture = capture
        self._provider = provider
        self._capture_seconds = capture_seconds

    @Slot(int)
    def run_operation(self, operation_id: int) -> None:
        try:
            captured = self._capture.capture(
                self._capture_seconds,
                is_interrupted=lambda: QThread.currentThread().isInterruptionRequested(),
            )
        except AppError as exc:
            self.failed.emit(operation_id, exc)
            return
        except Exception as exc:  # noqa: BLE001 - any unexpected capture failure must not kill the thread
            self.failed.emit(operation_id, AppError(AppErrorCode.INTERNAL_ERROR, str(exc)))
            return

        if is_silent(captured.metrics):
            self.no_audio.emit(operation_id)
            return

        self.capture_complete.emit(operation_id)
        wav_bytes = encode_wav(captured.pcm, captured.format)
        del captured

        track: Track | None
        try:
            track = asyncio.run(self._provider.recognize(wav_bytes))
        except AppError as exc:
            self.failed.emit(operation_id, exc)
            return
        except Exception as exc:  # noqa: BLE001 - unofficial provider API, map any failure
            self.failed.emit(operation_id, AppError(AppErrorCode.INTERNAL_ERROR, str(exc)))
            return
        finally:
            del wav_bytes

        if track is None:
            self.not_found.emit(operation_id)
        else:
            self.found.emit(operation_id, track)
