from __future__ import annotations

from PySide6.QtCore import Qt

from songkey.app.state import AppState, ViewState
from songkey.recognition.models import Track
from songkey.ui.overlay import OverlayWindow

TRACK = Track(provider_id="1", title="Song", artist="Artist", cover_url=None, provider_url="https://shazam.example/1")


def test_window_flags_never_accept_focus_and_stay_frameless(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def test_capturing_shows_bubble_transparent_to_mouse(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))

    assert overlay._bubble.isVisible()
    assert not overlay._card.isVisible()
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_recognizing_keeps_bubble_visible(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    overlay.apply_view_state(ViewState(state=AppState.RECOGNIZING, operation_id=1))

    assert overlay._bubble.isVisible()
    assert overlay._bubble._recognizing is True


def test_found_shows_card_and_accepts_mouse(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.FOUND, operation_id=1, track=TRACK))

    assert overlay._card.isVisible()
    assert not overlay._bubble.isVisible()
    assert not overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_idle_hides_everything_when_not_hovered(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.FOUND, operation_id=1, track=TRACK))

    overlay.apply_view_state(ViewState(state=AppState.IDLE, operation_id=1))

    assert not overlay.isVisible()


def test_idle_dismiss_deferred_while_card_is_hovered(qtbot, monkeypatch):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.FOUND, operation_id=1, track=TRACK))
    monkeypatch.setattr(overlay._card, "underMouse", lambda: True)

    overlay.apply_view_state(ViewState(state=AppState.IDLE, operation_id=1))
    assert overlay._card.isVisible()  # not hidden yet -- still hovered

    from PySide6.QtCore import QEvent

    overlay.leaveEvent(QEvent(QEvent.Type.Leave))
    assert not overlay.isVisible()


def test_no_match_shows_status_card(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.NOT_FOUND, operation_id=1))

    assert overlay._card.isVisible()
    assert overlay._card._status_label.text() == "No match found"


def test_error_shows_message_from_view_state(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.ERROR, operation_id=1, message="You're offline"))

    assert overlay._card._status_label.text() == "You're offline"


def test_bubble_pulse_property_changes_when_listening(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    initial = overlay._bubble.pulse

    def pulse_changed():
        return overlay._bubble.pulse != initial

    qtbot.waitUntil(pulse_changed, timeout=2000)


def test_found_card_shows_exact_title_and_artist(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.FOUND, operation_id=1, track=TRACK))

    assert overlay._card._title_label.text() == "Song"
    assert overlay._card._artist_label.text() == "Artist"


def test_found_card_renders_fallback_cover_immediately(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.FOUND, operation_id=1, track=TRACK))

    assert not overlay._card._cover_label.pixmap().isNull()
