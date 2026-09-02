"""Headless CLI: press Enter to capture six seconds of system audio and
recognize it. Proves the capture -> recognize -> result pipeline works
repeatedly without ever writing audio to disk. Ctrl+C to quit."""

from __future__ import annotations

import asyncio
import sys

from songkey.app.errors import AppError
from songkey.audio.silence import is_silent
from songkey.audio.wasapi import WasapiCapture
from songkey.audio.wav import encode_wav
from songkey.recognition.shazam import ShazamRecognitionProvider

CAPTURE_SECONDS = 6.0


def run_once(capture: WasapiCapture, provider: ShazamRecognitionProvider) -> None:
    captured = capture.capture(CAPTURE_SECONDS)
    print(
        f"Captured {captured.metrics.duration_seconds:.2f}s, "
        f"peak={captured.metrics.peak}, normalized_rms={captured.metrics.normalized_rms:.5f}"
    )

    if is_silent(captured.metrics):
        print("No audio is playing.")
        return

    wav_bytes = encode_wav(captured.pcm, captured.format)
    track = asyncio.run(provider.recognize(wav_bytes))

    if track is None:
        print("No match found.")
        return

    print(f"{track.artist} — {track.title}")
    if track.provider_url:
        print(f"  {track.provider_url}")


def main() -> int:
    provider = ShazamRecognitionProvider()
    with WasapiCapture() as capture:
        print("Press Enter to recognize (Ctrl+C to quit)...")
        try:
            while True:
                input()
                try:
                    run_once(capture, provider)
                except AppError as exc:
                    print(f"Error: {exc.user_message}")
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
