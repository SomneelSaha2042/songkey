from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Track:
    provider_id: str | None
    title: str
    artist: str
    cover_url: str | None
    provider_url: str | None
