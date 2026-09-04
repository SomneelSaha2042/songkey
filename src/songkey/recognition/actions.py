from __future__ import annotations

from urllib.parse import quote

from songkey.recognition.models import Track


def shazam_url(track: Track) -> str | None:
    return track.provider_url


def spotify_search_url(track: Track) -> str:
    # safe="" because the query sits in a URL *path* segment here, not a
    # query string -- an unescaped "/" (e.g. in "AC/DC") would otherwise be
    # read as an extra path segment.
    return f"https://open.spotify.com/search/{quote(f'{track.artist} {track.title}', safe='')}"


def youtube_search_url(track: Track) -> str:
    return f"https://www.youtube.com/results?search_query={quote(f'{track.artist} {track.title}', safe='')}"


def copy_text(track: Track) -> str:
    return f"{track.artist} — {track.title}"
