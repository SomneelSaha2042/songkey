"""Milestone-0 spike: resolve default WASAPI loopback device, capture N
seconds, print format/RMS/duration. Optionally save the capture to a WAV
file when --save is passed explicitly.

Usage:
    python scripts/diagnose_audio.py [--seconds 6] [--save out.wav]
"""

from __future__ import annotations

import argparse
import io
import sys
import wave

import numpy as np
import pyaudiowpatch as pyaudio

FRAMES_PER_BUFFER = 1024
SAMPLE_FORMAT = pyaudio.paInt16
SAMPLE_WIDTH = 2  # bytes, matches paInt16


def resolve_loopback_device(pa: pyaudio.PyAudio) -> dict:
    try:
        wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError as exc:
        raise SystemExit(f"WASAPI host API not available: {exc}") from exc

    device = pa.get_default_wasapi_loopback()
    if device is None:
        raise SystemExit("No default WASAPI loopback endpoint found")

    if device.get("maxInputChannels", 0) < 1:
        raise SystemExit(f"Loopback device has no input channels: {device}")

    rate = device.get("defaultSampleRate", 0)
    if not rate or rate <= 0:
        raise SystemExit(f"Loopback device has invalid sample rate: {device}")

    print(f"WASAPI host API: {wasapi_info['name']}")
    print(f"Loopback device: {device['name']} (index {device['index']})")
    print(f"  channels: {device['maxInputChannels']}")
    print(f"  native sample rate: {int(rate)} Hz")
    return device


def capture(pa: pyaudio.PyAudio, device: dict, seconds: float) -> tuple[bytes, int, int]:
    channels = device["maxInputChannels"]
    rate = int(device["defaultSampleRate"])

    stream = pa.open(
        format=SAMPLE_FORMAT,
        channels=channels,
        rate=rate,
        input=True,
        input_device_index=device["index"],
        frames_per_buffer=FRAMES_PER_BUFFER,
    )

    frames: list[bytes] = []
    total_frames = int(rate * seconds)
    read = 0
    try:
        while read < total_frames:
            chunk = min(FRAMES_PER_BUFFER, total_frames - read)
            data = stream.read(chunk)
            frames.append(data)
            read += chunk
    finally:
        stream.stop_stream()
        stream.close()

    return b"".join(frames), rate, channels


def report_metrics(pcm: bytes, rate: int, channels: int, seconds: float) -> None:
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size == 0:
        print("No samples captured.")
        return

    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    normalized_rms = rms / 32768.0
    actual_duration = samples.size / channels / rate

    print(f"Captured {samples.size} samples ({actual_duration:.2f}s actual, {seconds:.2f}s requested)")
    print(f"Peak amplitude: {peak} / 32767")
    print(f"RMS: {rms:.1f}  (normalized: {normalized_rms:.5f})")
    if peak == 0:
        print("Result: SILENT (all-zero buffer)")
    else:
        print("Result: audio present")


def build_wav(pcm: bytes, rate: int, channels: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--save", type=str, default=None, help="Path to save captured WAV (explicit opt-in only)")
    args = parser.parse_args()

    pa = pyaudio.PyAudio()
    try:
        device = resolve_loopback_device(pa)
        print(f"\nCapturing {args.seconds}s from default output mix... (play some audio now)")
        pcm, rate, channels = capture(pa, device, args.seconds)
    finally:
        pa.terminate()

    report_metrics(pcm, rate, channels, args.seconds)

    if args.save:
        wav_bytes = build_wav(pcm, rate, channels)
        with open(args.save, "wb") as f:
            f.write(wav_bytes)
        print(f"Saved: {args.save} ({len(wav_bytes)} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
