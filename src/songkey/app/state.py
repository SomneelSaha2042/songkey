from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from songkey.recognition.models import Track


class AppState(Enum):
    IDLE = auto()
    CAPTURING = auto()
    RECOGNIZING = auto()
    FOUND = auto()
    NOT_FOUND = auto()
    NO_AUDIO = auto()
    ERROR = auto()


TERMINAL_STATES = frozenset({AppState.FOUND, AppState.NOT_FOUND, AppState.NO_AUDIO, AppState.ERROR})


@dataclass(frozen=True, slots=True)
class ViewState:
    state: AppState
    operation_id: int
    track: Track | None = None
    message: str | None = None
