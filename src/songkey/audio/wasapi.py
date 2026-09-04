from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Self

import pyaudiowpatch as pyaudio

from songkey.app.errors import AppError, AppErrorCode
from songkey.audio.models import AudioFormat, CapturedAudio
from songkey.audio.silence import compute_metrics

FRAMES_PER_BUFFER = 1024
SAMPLE_FORMAT = pyaudio.paInt16

# Some WASAPI drivers stall the loopback clock when the output device has no
# active audio session (nothing rendering at all). A blocking stream.read()
# can then hang far past the requested capture length instead of returning
# silence -- reproduced live by muting all audio and triggering a capture,
# which hung for 113 seconds before failing. Bound the whole read loop so
# failure surfaces as a normal CAPTURE_FAILED error instead of the app
# looking frozen.
READ_TIMEOUT_BUFFER_SECONDS = 3.0


def _run_with_timeout[T](fn: Callable[[], T], timeout_seconds: float) -> T:
    """Runs `fn` in a helper thread and enforces `timeout_seconds`. On
    timeout the helper thread is abandoned rather than joined — it may still
    be blocked in a driver call that never returns, and waiting for it would
    reintroduce the exact hang this exists to avoid."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn)
    try:
        result = future.result(timeout=timeout_seconds)
    except TimeoutError:
        pool.shutdown(wait=False)
        raise
    pool.shutdown(wait=False)
    return result


class WasapiCapture:
    """AudioCapture adapter over PyAudioWPatch WASAPI loopback. The only
    module allowed to import pyaudiowpatch."""

    def __init__(self) -> None:
        self._pa = pyaudio.PyAudio()
        # ponytail: set once a read times out and its thread is abandoned
        # (see _run_with_timeout). PortAudio is not safe to terminate while
        # another thread may still be blocked inside a call on this same
        # host instance — doing so segfaults the process. Skip terminate()
        # for the rest of this instance's life; the handle leaks, but the
        # process is exiting anyway. Fix properly if leaked-thread volume
        # ever matters: give each capture() its own PyAudio() instance.
        self._abandoned_stream = False

    def close(self) -> None:
        if self._abandoned_stream:
            return
        self._pa.terminate()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _resolve_device(self) -> dict:
        try:
            self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError as exc:
            raise AppError(AppErrorCode.WASAPI_UNAVAILABLE, str(exc)) from exc

        device = self._pa.get_default_wasapi_loopback()
        if device is None:
            raise AppError(AppErrorCode.DEVICE_UNAVAILABLE, "no default WASAPI loopback endpoint")

        if device.get("maxInputChannels", 0) < 1:
            raise AppError(AppErrorCode.DEVICE_UNAVAILABLE, f"no input channels: {device.get('name')}")

        rate = device.get("defaultSampleRate", 0)
        if not rate or rate <= 0:
            raise AppError(AppErrorCode.DEVICE_UNAVAILABLE, f"invalid sample rate: {device.get('name')}")

        return device

    def capture(self, seconds: float, is_interrupted: Callable[[], bool] | None = None) -> CapturedAudio:
        try:
            return self._capture_once(seconds, is_interrupted)
        except (TimeoutError, AppError):
            # A long-lived PortAudio host can go stale relative to the OS
            # audio engine -- after a Bluetooth reconnect/codec switch, or
            # simply after the default output device changes (e.g.
            # switching from Bluetooth headphones to speakers). Device
            # enumeration can then fail outright (DEVICE_UNAVAILABLE) or
            # "succeed" against a stale endpoint that just hangs on read
            # (the TimeoutError case). Reproduced live both ways: a
            # brand-new PyAudio() instance resolved and captured fine
            # seconds after the running app's own calls kept failing.
            # Recreate the host once and retry; abandon (do not terminate)
            # the old one, since a helper thread from a timed-out read may
            # still be blocked inside it.
            self._abandoned_stream = True
            self._pa = pyaudio.PyAudio()
            try:
                return self._capture_once(seconds, is_interrupted)
            except TimeoutError as exc:
                raise AppError(
                    AppErrorCode.CAPTURE_FAILED, "WASAPI read timed out twice (no active audio session on output device)"
                ) from exc

    def _capture_once(self, seconds: float, is_interrupted: Callable[[], bool] | None) -> CapturedAudio:
        device = self._resolve_device()

        channels = device["maxInputChannels"]
        rate = int(device["defaultSampleRate"])
        audio_format = AudioFormat(sample_rate=rate, channels=channels)

        try:
            stream = self._pa.open(
                format=SAMPLE_FORMAT,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
        except OSError:
            # Endpoint disappeared between lookup and open: re-resolve once.
            device = self._resolve_device()
            channels = device["maxInputChannels"]
            rate = int(device["defaultSampleRate"])
            audio_format = AudioFormat(sample_rate=rate, channels=channels)
            try:
                stream = self._pa.open(
                    format=SAMPLE_FORMAT,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=device["index"],
                    frames_per_buffer=FRAMES_PER_BUFFER,
                )
            except OSError as exc:
                raise AppError(AppErrorCode.DEVICE_UNAVAILABLE, str(exc)) from exc

        total_frames = int(rate * seconds)

        def read_all() -> tuple[bytes, int]:
            frames: list[bytes] = []
            read = 0
            while read < total_frames:
                if is_interrupted is not None and is_interrupted():
                    break
                chunk = min(FRAMES_PER_BUFFER, total_frames - read)
                frames.append(stream.read(chunk))
                read += chunk
            return b"".join(frames), read

        try:
            pcm, read = _run_with_timeout(read_all, seconds + READ_TIMEOUT_BUFFER_SECONDS)
        except TimeoutError:
            # Deliberately do not touch `stream` here: the read thread may
            # still be blocked inside it, and closing now would race a live
            # driver call. It is abandoned along with the helper thread.
            # Let the caller (capture()) decide whether to retry.
            raise
        except OSError as exc:
            stream.stop_stream()
            stream.close()
            raise AppError(AppErrorCode.CAPTURE_FAILED, str(exc)) from exc
        else:
            stream.stop_stream()
            stream.close()

        actual_duration = read / rate if rate else 0.0
        metrics = compute_metrics(pcm, audio_format, actual_duration)
        return CapturedAudio(pcm=pcm, format=audio_format, metrics=metrics)
