from __future__ import annotations

import pytest

from songkey.app.errors import AppError, AppErrorCode
from songkey.recognition.models import Track
from songkey.recognition.parser import parse_shazam_response


def test_match_fixture_returns_expected_track(load_provider_fixture):
    result = load_provider_fixture("match.json")

    track = parse_shazam_response(result)

    assert track == Track(
        provider_id="315646975",
        title="One Dance (feat. Wizkid & Kyla)",
        artist="Drake",
        cover_url="https://example.test/cover.jpg",
        provider_url="https://www.shazam.com/track/315646975/one-dance-feat-wizkid-kyla",
    )


def test_empty_matches_return_none(load_provider_fixture):
    result = load_provider_fixture("no_match.json")

    assert parse_shazam_response(result) is None


def test_missing_matches_key_returns_none():
    assert parse_shazam_response({}) is None


def test_missing_title_raises_provider_response_invalid(load_provider_fixture):
    result = load_provider_fixture("malformed.json")

    with pytest.raises(AppError) as exc_info:
        parse_shazam_response(result)

    assert exc_info.value.code is AppErrorCode.PROVIDER_RESPONSE_INVALID


def test_missing_artwork_and_url_still_returns_valid_track():
    result = {
        "matches": [{"id": "1"}],
        "track": {"key": "1", "title": "Song", "subtitle": "Artist"},
    }

    track = parse_shazam_response(result)

    assert track == Track(provider_id="1", title="Song", artist="Artist", cover_url=None, provider_url=None)


def test_extra_provider_fields_do_not_change_parsing():
    result = {
        "matches": [{"id": "1", "offset": 12.3, "timeskew": 0.01}],
        "track": {
            "key": "1",
            "title": "Song",
            "subtitle": "Artist",
            "genres": {"primary": "Pop"},
            "hub": {"actions": []},
        },
    }

    track = parse_shazam_response(result)

    assert track == Track(provider_id="1", title="Song", artist="Artist", cover_url=None, provider_url=None)
