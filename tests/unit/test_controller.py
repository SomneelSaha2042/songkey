from __future__ import annotations

from songkey.app.controller import AppController
from songkey.app.errors import AppError, AppErrorCode
from songkey.app.state import AppState, ViewState
from songkey.recognition.models import Track

TRACK = Track(provider_id="1", title="Song", artist="Artist", cover_url=None, provider_url=None)


class FakeScheduler:
    """Records scheduled callbacks instead of firing them; tests fire them
    explicitly by operation id or seconds."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def __call__(self, seconds: float, callback) -> None:
        self.scheduled.append((seconds, callback))

    def fire_last(self) -> None:
        self.scheduled[-1][1]()


def make_controller(dismiss_seconds=None):
    scheduler = FakeScheduler()
    starts: list[int] = []
    view_states: list[ViewState] = []
    controller = AppController(
        schedule_timer=scheduler,
        start_operation=starts.append,
        on_view_state=view_states.append,
        dismiss_seconds=dismiss_seconds,
    )
    return controller, scheduler, starts, view_states


def test_idle_trigger_starts_capturing_and_requests_operation():
    controller, _scheduler, starts, view_states = make_controller()

    controller.trigger()

    assert controller.state is AppState.CAPTURING
    assert starts == [1]
    assert view_states[-1] == ViewState(state=AppState.CAPTURING, operation_id=1)


def test_second_trigger_is_ignored_while_capturing():
    controller, _scheduler, starts, _view_states = make_controller()

    controller.trigger()
    controller.trigger()

    assert controller.state is AppState.CAPTURING
    assert starts == [1]


def test_second_trigger_is_ignored_while_recognizing():
    controller, _scheduler, starts, _view_states = make_controller()

    controller.trigger()
    controller.on_capture_complete(1)
    controller.trigger()

    assert controller.state is AppState.RECOGNIZING
    assert starts == [1]


def test_capture_complete_moves_to_recognizing():
    controller, _scheduler, _starts, view_states = make_controller()
    controller.trigger()

    controller.on_capture_complete(1)

    assert controller.state is AppState.RECOGNIZING
    assert view_states[-1].state is AppState.RECOGNIZING


def test_no_audio_goes_directly_from_capturing_and_schedules_dismiss():
    controller, scheduler, _starts, view_states = make_controller()
    controller.trigger()

    controller.on_no_audio(1)

    assert controller.state is AppState.NO_AUDIO
    assert view_states[-1].state is AppState.NO_AUDIO
    assert scheduler.scheduled[-1][0] == 2.5


def test_found_carries_track_and_schedules_six_second_dismiss():
    controller, scheduler, _starts, view_states = make_controller()
    controller.trigger()
    controller.on_capture_complete(1)

    controller.on_found(1, TRACK)

    assert controller.state is AppState.FOUND
    assert view_states[-1].track == TRACK
    assert scheduler.scheduled[-1][0] == 6.0


def test_not_found_terminal_state():
    controller, _scheduler, _starts, view_states = make_controller()
    controller.trigger()
    controller.on_capture_complete(1)

    controller.on_not_found(1)

    assert controller.state is AppState.NOT_FOUND
    assert view_states[-1].state is AppState.NOT_FOUND


def test_failed_during_capturing_enters_error_with_message():
    controller, _scheduler, _starts, view_states = make_controller()
    controller.trigger()

    controller.on_failed(1, AppError(AppErrorCode.CAPTURE_FAILED))

    assert controller.state is AppState.ERROR
    assert view_states[-1].message == "Couldn't capture system audio"


def test_failed_during_recognizing_enters_error():
    controller, _scheduler, _starts, _view_states = make_controller()
    controller.trigger()
    controller.on_capture_complete(1)

    controller.on_failed(1, AppError(AppErrorCode.OFFLINE))

    assert controller.state is AppState.ERROR


def test_dismiss_timer_returns_to_idle():
    controller, scheduler, _starts, view_states = make_controller()
    controller.trigger()
    controller.on_capture_complete(1)
    controller.on_not_found(1)

    scheduler.fire_last()

    assert controller.state is AppState.IDLE
    assert view_states[-1].state is AppState.IDLE


def test_stale_operation_id_is_ignored_on_every_callback():
    controller, _scheduler, _starts, view_states = make_controller()
    controller.trigger()  # operation 1
    controller.on_capture_complete(1)
    controller.on_found(1, TRACK)  # -> FOUND, operation 1 still current
    before = list(view_states)

    # A late signal from a stale operation id must not affect current state.
    controller.on_capture_complete(0)
    controller.on_no_audio(0)
    controller.on_found(0, TRACK)
    controller.on_not_found(0)
    controller.on_failed(0, AppError(AppErrorCode.INTERNAL_ERROR))

    assert controller.state is AppState.FOUND
    assert view_states == before


def test_stale_dismiss_fired_twice_does_not_disturb_newer_operation():
    controller, scheduler, _starts, _view_states = make_controller()
    controller.trigger()
    controller.on_capture_complete(1)
    controller.on_not_found(1)
    op1_dismiss = scheduler.scheduled[-1][1]
    op1_dismiss()  # back to IDLE
    assert controller.state is AppState.IDLE

    controller.trigger()  # operation 2

    # A duplicate/late firing of operation 1's dismiss must not touch operation 2.
    op1_dismiss()

    assert controller.state is AppState.CAPTURING


def test_rapid_triggers_produce_exactly_one_operation():
    controller, _scheduler, starts, _view_states = make_controller()

    for _ in range(5):
        controller.trigger()

    assert starts == [1]
    assert controller.state is AppState.CAPTURING
