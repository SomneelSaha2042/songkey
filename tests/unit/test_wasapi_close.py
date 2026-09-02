from __future__ import annotations

from unittest.mock import MagicMock

from songkey.audio.wasapi import WasapiCapture


def _make_capture_with_fake_pa(monkeypatch) -> tuple[WasapiCapture, MagicMock]:
    fake_pa = MagicMock()
    monkeypatch.setattr("songkey.audio.wasapi.pyaudio.PyAudio", lambda: fake_pa)
    return WasapiCapture(), fake_pa


def test_close_terminates_pyaudio_normally(monkeypatch):
    capture, fake_pa = _make_capture_with_fake_pa(monkeypatch)

    capture.close()

    fake_pa.terminate.assert_called_once()


def test_close_skips_terminate_after_abandoned_stream(monkeypatch):
    """A timed-out capture() leaves a helper thread possibly still blocked
    inside a PortAudio call on this instance. Calling terminate() on it then
    can segfault the process — reproduced live during Milestone 2 testing
    (Quit crashed after a muted-audio capture timeout). close() must skip
    terminate() once that has happened."""
    capture, fake_pa = _make_capture_with_fake_pa(monkeypatch)
    capture._abandoned_stream = True

    capture.close()

    fake_pa.terminate.assert_not_called()
