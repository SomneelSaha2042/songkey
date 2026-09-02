from __future__ import annotations

from collections.abc import Callable
from typing import Self

import pyaudiowpatch as pyaudio

from songkey.app.errors import AppError, AppErrorCode
from songkey.audio.models import AudioFormat, CapturedAudio
from songkey.audio.silence import compute_metrics

FRAMES_PER_BUFFER = 1024
SAMPLE_FORMAT = pyaudio.paInt16


class WasapiCapture:
    """AudioCapture adapter over PyAudioWPatch WASAPI loopback. The only
    module allowed to import pyaudiowpatch."""

    def __init__(self) -> None:
        self._pa = pyaudio.PyAudio()

    def close(self) -> None:
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

        frames: list[bytes] = []
        total_frames = int(rate * seconds)
        read = 0
        try:
            while read < total_frames:
                if is_interrupted is not None and is_interrupted():
                    break
                chunk = min(FRAMES_PER_BUFFER, total_frames - read)
                frames.append(stream.read(chunk))
                read += chunk
        except OSError as exc:
            raise AppError(AppErrorCode.CAPTURE_FAILED, str(exc)) from exc
        finally:
            stream.stop_stream()
            stream.close()

        pcm = b"".join(frames)
        actual_duration = read / rate if rate else 0.0
        metrics = compute_metrics(pcm, audio_format, actual_duration)
        return CapturedAudio(pcm=pcm, format=audio_format, metrics=metrics)
