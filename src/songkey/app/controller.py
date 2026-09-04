from __future__ import annotations

from collections.abc import Callable, Mapping

from songkey.app.errors import AppError
from songkey.app.state import TERMINAL_STATES, AppState, ViewState
from songkey.recognition.models import Track

TimerScheduler = Callable[[float, Callable[[], None]], None]

DEFAULT_DISMISS_SECONDS: dict[AppState, float] = {
    AppState.FOUND: 6.0,
    AppState.NOT_FOUND: 2.5,
    AppState.NO_AUDIO: 2.5,
    AppState.ERROR: 4.0,
}


class AppController:
    """Owns state transitions and operation IDs. Never imports PySide6,
    PyAudioWPatch, or ShazamIO — it depends only on injected callables, so
    it is fully testable without Qt or real hardware.

    `start_operation` is called with a fresh operation ID when a trigger is
    accepted; the caller (production: a Qt bridge to the worker thread) is
    responsible for actually running capture + recognition and reporting
    back through `on_capture_complete` / `on_no_audio` / `on_found` /
    `on_not_found` / `on_failed`. Results carrying a stale operation ID
    (superseded by a newer trigger, or by `cancel()`) are ignored.
    """

    def __init__(
        self,
        schedule_timer: TimerScheduler,
        start_operation: Callable[[int], None],
        on_view_state: Callable[[ViewState], None],
        request_cancel: Callable[[int], None],
        dismiss_seconds: Mapping[AppState, float] | None = None,
    ) -> None:
        self._schedule_timer = schedule_timer
        self._start_operation = start_operation
        self._on_view_state = on_view_state
        self._request_cancel = request_cancel
        self._dismiss_seconds = dict(dismiss_seconds or DEFAULT_DISMISS_SECONDS)
        self._state = AppState.IDLE
        self._operation_id = 0

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def operation_id(self) -> int:
        return self._operation_id

    def trigger(self) -> None:
        if self._state is not AppState.IDLE:
            return
        self._operation_id += 1
        self._transition(AppState.CAPTURING)
        self._start_operation(self._operation_id)

    def cancel(self) -> None:
        """User-initiated abort (clicking the listening/recognizing orb) --
        distinct from a normal terminal state: returns straight to IDLE
        with no dismiss timer, and bumps the operation ID so a worker
        result that was already in flight is ignored on arrival, the same
        way a stale/superseded trigger is."""
        if self._state not in (AppState.CAPTURING, AppState.RECOGNIZING):
            return
        self._request_cancel(self._operation_id)
        self._operation_id += 1
        self._transition(AppState.IDLE)

    def on_capture_complete(self, operation_id: int) -> None:
        if not self._is_current(operation_id) or self._state is not AppState.CAPTURING:
            return
        self._transition(AppState.RECOGNIZING)

    def on_no_audio(self, operation_id: int) -> None:
        if not self._is_current(operation_id) or self._state is not AppState.CAPTURING:
            return
        self._enter_terminal(AppState.NO_AUDIO)

    def on_found(self, operation_id: int, track: Track) -> None:
        if not self._is_current(operation_id) or self._state is not AppState.RECOGNIZING:
            return
        self._enter_terminal(AppState.FOUND, track=track)

    def on_not_found(self, operation_id: int) -> None:
        if not self._is_current(operation_id) or self._state is not AppState.RECOGNIZING:
            return
        self._enter_terminal(AppState.NOT_FOUND)

    def on_failed(self, operation_id: int, error: AppError) -> None:
        if not self._is_current(operation_id) or self._state not in (AppState.CAPTURING, AppState.RECOGNIZING):
            return
        self._enter_terminal(AppState.ERROR, message=error.user_message)

    def _is_current(self, operation_id: int) -> bool:
        return operation_id == self._operation_id

    def _enter_terminal(self, state: AppState, track: Track | None = None, message: str | None = None) -> None:
        self._transition(state, track=track, message=message)
        operation_id = self._operation_id
        seconds = self._dismiss_seconds[state]
        self._schedule_timer(seconds, lambda: self._dismiss(operation_id))

    def _dismiss(self, operation_id: int) -> None:
        if not self._is_current(operation_id) or self._state not in TERMINAL_STATES:
            return
        self._transition(AppState.IDLE)

    def _transition(self, state: AppState, track: Track | None = None, message: str | None = None) -> None:
        self._state = state
        self._on_view_state(ViewState(state=state, operation_id=self._operation_id, track=track, message=message))
