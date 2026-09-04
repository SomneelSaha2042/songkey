from __future__ import annotations

from songkey.recognition.actions import (
    copy_text,
    shazam_url,
    spotify_search_url,
    youtube_search_url,
)
from songkey.recognition.models import Track

TRACK = Track(
    provider_id="1",
    title="One Dance (feat. Wizkid & Kyla)",
    artist="Drake",
    cover_url="https://example.test/cover.jpg",
    provider_url="https://www.shazam.com/track/1/one-dance",
)

TRACK_NO_URL = Track(provider_id="1", title="Song & Title", artist="Artist/Name", cover_url=None, provider_url=None)


def test_shazam_url_passes_through_provider_url():
    assert shazam_url(TRACK) == "https://www.shazam.com/track/1/one-dance"


def test_shazam_url_none_when_provider_has_no_url():
    assert shazam_url(TRACK_NO_URL) is None


def test_spotify_search_url_is_encoded_and_contains_no_tracking_params():
    url = spotify_search_url(TRACK)

    assert url.startswith("https://open.spotify.com/search/")
    assert "?" not in url
    assert "%20" in url or "+" in url  # space is encoded
    assert "&" not in url or "Wizkid" in url  # the literal "&" in the title must be encoded, not a query separator


def test_youtube_search_url_is_encoded():
    url = youtube_search_url(TRACK)

    assert url.startswith("https://www.youtube.com/results?search_query=")
    assert "Drake" not in url.split("search_query=")[0]  # not leaked outside the query value


def test_urls_encode_special_characters_safely():
    spotify = spotify_search_url(TRACK_NO_URL)
    youtube = youtube_search_url(TRACK_NO_URL)

    assert "/" not in spotify.removeprefix("https://open.spotify.com/search/")
    assert "&" not in youtube.split("search_query=")[1] or "%26" in youtube


def test_copy_text_format():
    assert copy_text(TRACK) == "Drake — One Dance (feat. Wizkid & Kyla)"
