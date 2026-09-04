from __future__ import annotations

from unittest.mock import MagicMock

from songkey.audio.wasapi import WasapiCapture

DEVICE = {"maxInputChannels": 2, "defaultSampleRate": 48000.0, "index": 0, "name": "Fake [Loopback]"}


def _working_pa() -> MagicMock:
    pa = MagicMock()
    pa.get_default_wasapi_loopback.return_value = DEVICE
    stream = MagicMock()
    stream.read.return_value = b"\x00\x00" * 1024
    pa.open.return_value = stream
    return pa


def _broken_pa() -> MagicMock:
    """Simulates a stale PortAudio host: device resolution fails outright,
    with no stream ever opened -- matches the real bug where a device
    change during a running session leaves get_default_wasapi_loopback()
    unable to find the (still cached-stale) default device."""
    pa = MagicMock()
    pa.get_default_wasapi_loopback.return_value = None
    return pa


def test_retry_after_appError_terminates_the_stale_host_first(monkeypatch):
    """The actual bug: without terminating the old host, PortAudio's device
    scan (done once, at Pa_Initialize()) never refreshes, so every "fresh"
    PyAudio() object in the same process keeps returning the same stale
    device list. Reproduced live -- fixed by terminating the broken host
    before constructing the replacement."""
    broken = _broken_pa()
    working = _working_pa()
    hosts = iter([broken, working])
    monkeypatch.setattr("songkey.audio.wasapi.pyaudio.PyAudio", lambda: next(hosts))

    capture = WasapiCapture()
    result = capture.capture(0.01)

    broken.terminate.assert_called_once()
    assert result.pcm  # succeeded via the second (working) host


def test_retry_after_timeout_does_not_terminate_the_stale_host(monkeypatch):
    """A timed-out read may still have a helper thread blocked inside the
    old host; terminating it would race that thread and can segfault (see
    _run_with_timeout / the Milestone 2 close() fix). Only AppError retries
    -- where no stream/thread was ever created -- terminate safely."""
    stuck = MagicMock()
    stuck.get_default_wasapi_loopback.return_value = DEVICE
    stuck_stream = MagicMock()

    def hang_forever(chunk):
        import time

        time.sleep(10)
        return b""

    stuck_stream.read.side_effect = hang_forever
    stuck.open.return_value = stuck_stream

    working = _working_pa()
    hosts = iter([stuck, working])
    monkeypatch.setattr("songkey.audio.wasapi.pyaudio.PyAudio", lambda: next(hosts))
    monkeypatch.setattr("songkey.audio.wasapi.READ_TIMEOUT_BUFFER_SECONDS", 0.05)

    capture = WasapiCapture()
    result = capture.capture(0.01)

    stuck.terminate.assert_not_called()
    assert capture._abandoned_stream is True
    assert result.pcm  # succeeded via the second (working) host
