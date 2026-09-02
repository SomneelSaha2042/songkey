from __future__ import annotations

from songkey.app.errors import AppError, AppErrorCode
from songkey.recognition.models import Track


def parse_shazam_response(result: dict) -> Track | None:
    """Translate a raw ShazamIO response dict into a Track, or None for no match.

    Raises AppError(PROVIDER_RESPONSE_INVALID) when matches are present but the
    track payload is missing the fields required to build a usable result.
    """
    matches = result.get("matches") or []
    if not matches:
        return None

    track = result.get("track") or {}
    title = track.get("title")
    artist = track.get("subtitle")
    if not title or not artist:
        raise AppError(AppErrorCode.PROVIDER_RESPONSE_INVALID, "matches present but track missing title/subtitle")

    images = track.get("images") or {}
    return Track(
        provider_id=track.get("key"),
        title=title,
        artist=artist,
        cover_url=images.get("coverart"),
        provider_url=track.get("url"),
    )
