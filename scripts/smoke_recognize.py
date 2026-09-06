"""Milestone-0 spike: pass a user-supplied WAV file as bytes to the pinned
ShazamIO version and print the normalized result.

Usage:
    python scripts/smoke_recognize.py path\\to\\clip.wav
"""

from __future__ import annotations

import asyncio
import sys

from shazamio import Shazam

TIMEOUT_SECONDS = 12.0


def extract_track(result: dict) -> dict | None:
    matches = result.get("matches") or []
    if not matches:
        return None

    track = result.get("track") or {}
    title = track.get("title")
    artist = track.get("subtitle")
    if not title or not artist:
        return None

    images = track.get("images") or {}
    return {
        "title": title,
        "artist": artist,
        "cover_url": images.get("coverart"),
        "provider_url": track.get("url"),
    }


async def main_async(wav_path: str) -> int:
    with open(wav_path, "rb") as f:  # noqa: ASYNC230 - one-shot spike script, reads once at startup
        wav_bytes = f.read()

    print(f"Read {len(wav_bytes)} bytes from {wav_path}")

    shazam = Shazam()
    try:
        result = await asyncio.wait_for(shazam.recognize(wav_bytes), timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        print(f"FAILED: recognition timed out after {TIMEOUT_SECONDS}s")
        return 1
    except Exception as exc:  # noqa: BLE001 - spike script, want to see any provider error
        print(f"FAILED: provider error: {exc!r}")
        return 1

    track = extract_track(result)
    if track is None:
        print("No match found.")
        return 0

    print("Match found:")
    print(f"  Title:  {track['title']}")
    print(f"  Artist: {track['artist']}")
    print(f"  Cover:  {track['cover_url']}")
    print(f"  URL:    {track['provider_url']}")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_recognize.py path\\to\\clip.wav")
        return 2
    return asyncio.run(main_async(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
