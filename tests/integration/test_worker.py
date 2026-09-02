from __future__ import annotations

import pytest

from songkey.app.errors import AppError, AppErrorCode
from songkey.audio.models import AudioFormat, CapturedAudio, CaptureMetrics
from songkey.recognition.models import Track
from songkey.runtime.worker import RecognitionWorker

TRACK = Track(provider_id="1", title="Song", artist="Artist", cover_url=None, provider_url=None)
FORMAT = AudioFormat(sample_rate=48000, channels=2, sample_width=2)


def _captured_audio(peak: int, normalized_rms: float) -> CapturedAudio:
    metrics = CaptureMetrics(peak=peak, rms=normalized_rms * 32768.0, normalized_rms=normalized_rms, duration_seconds=6.0)
    return CapturedAudio(pcm=b"\x00\x01" * 100, format=FORMAT, metrics=metrics)


class FakeCapture:
    def __init__(self, result=None, error: AppError | None = None) -> None:
        self._result = result
        self._error = error
        self.call_count = 0

    def capture(self, seconds: float, is_interrupted=None) -> CapturedAudio:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeProvider:
    def __init__(self, track: Track | None = None, error: AppError | None = None) -> None:
        self._track = track
        self._error = error
        self.call_count = 0

    async def recognize(self, wav_bytes: bytes) -> Track | None:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return self._track


@pytest.fixture
def signal_recorder():
    def _connect_all(worker: RecognitionWorker) -> dict[str, list]:
        events: dict[str, list] = {name: [] for name in ("capture_complete", "no_audio", "found", "not_found", "failed")}
        worker.capture_complete.connect(lambda op: events["capture_complete"].append(op))
        worker.no_audio.connect(lambda op: events["no_audio"].append(op))
        worker.found.connect(lambda op, track: events["found"].append((op, track)))
        worker.not_found.connect(lambda op: events["not_found"].append(op))
        worker.failed.connect(lambda op, error: events["failed"].append((op, error)))
        return events

    return _connect_all


def test_match_emits_capture_complete_then_found(qapp, signal_recorder):
    capture = FakeCapture(result=_captured_audio(peak=20000, normalized_rms=0.05))
    provider = FakeProvider(track=TRACK)
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(7)

    assert events["capture_complete"] == [7]
    assert events["found"] == [(7, TRACK)]
    assert events["no_audio"] == []
    assert events["not_found"] == []
    assert events["failed"] == []


def test_no_match_emits_not_found(qapp, signal_recorder):
    capture = FakeCapture(result=_captured_audio(peak=20000, normalized_rms=0.05))
    provider = FakeProvider(track=None)
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(1)

    assert events["capture_complete"] == [1]
    assert events["not_found"] == [1]


def test_silent_capture_skips_recognition_entirely(qapp, signal_recorder):
    capture = FakeCapture(result=_captured_audio(peak=0, normalized_rms=0.0))
    provider = FakeProvider(track=TRACK)
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(1)

    assert events["no_audio"] == [1]
    assert events["capture_complete"] == []
    assert provider.call_count == 0


def test_capture_failure_emits_failed(qapp, signal_recorder):
    capture = FakeCapture(error=AppError(AppErrorCode.DEVICE_UNAVAILABLE))
    provider = FakeProvider(track=TRACK)
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(1)

    assert len(events["failed"]) == 1
    op_id, error = events["failed"][0]
    assert op_id == 1
    assert error.code is AppErrorCode.DEVICE_UNAVAILABLE
    assert provider.call_count == 0


def test_recognition_failure_emits_failed_after_capture_complete(qapp, signal_recorder):
    capture = FakeCapture(result=_captured_audio(peak=20000, normalized_rms=0.05))
    provider = FakeProvider(error=AppError(AppErrorCode.OFFLINE))
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(1)

    assert events["capture_complete"] == [1]
    _op_id, error = events["failed"][0]
    assert error.code is AppErrorCode.OFFLINE


def test_unexpected_capture_exception_maps_to_internal_error(qapp, signal_recorder):
    capture = FakeCapture(error=RuntimeError("boom"))
    provider = FakeProvider(track=TRACK)
    worker = RecognitionWorker(capture, provider)
    events = signal_recorder(worker)

    worker.run_operation(1)

    _op_id, error = events["failed"][0]
    assert error.code is AppErrorCode.INTERNAL_ERROR
