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


def test_capturing_shows_bubble_and_accepts_clicks_for_cancel(qtbot):
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)

    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))

    assert overlay._bubble.isVisible()
    assert not overlay._card.isVisible()
    # Clickable (to cancel a misclicked trigger) even though the window
    # flags mean it never steals keyboard focus from the foreground app.
    assert not overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


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


def test_clicking_bubble_invokes_on_cancel(qtbot):
    cancelled = []
    overlay = OverlayWindow(on_cancel=lambda: cancelled.append(True))
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))

    overlay._bubble.clicked.emit()

    assert cancelled == [True]


def test_click_leaves_a_dim_idle_bubble_visible(qtbot):
    overlay = OverlayWindow(on_cancel=lambda: None)
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))

    overlay._bubble.clicked.emit()

    assert overlay.isVisible()
    assert overlay._bubble.isVisible()
    assert overlay._bubble._idle is True


def test_subsequent_idle_view_state_does_not_hide_the_idle_bubble(qtbot):
    overlay = OverlayWindow(on_cancel=lambda: None)
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    overlay._bubble.clicked.emit()

    # The controller's own IDLE transition (from cancel()) arrives after --
    # it must not clobber the idle-bubble affordance we're deliberately
    # keeping up.
    overlay.apply_view_state(ViewState(state=AppState.IDLE, operation_id=2))

    assert overlay.isVisible()
    assert overlay._bubble.isVisible()


def test_clicking_idle_bubble_triggers_a_new_listen(qtbot):
    triggered = []
    overlay = OverlayWindow(on_cancel=lambda: None, on_trigger=lambda: triggered.append(True))
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    overlay._bubble.clicked.emit()  # -> idle bubble

    overlay._bubble.clicked.emit()  # -> restart

    assert triggered == [True]
    assert not overlay.isVisible()


def test_mouse_leaving_idle_bubble_dismisses_it(qtbot):
    from PySide6.QtCore import QEvent

    overlay = OverlayWindow(on_cancel=lambda: None)
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    overlay._bubble.clicked.emit()  # -> idle bubble
    assert overlay.isVisible()

    overlay.leaveEvent(QEvent(QEvent.Type.Leave))

    assert not overlay.isVisible()


def test_new_trigger_clears_idle_bubble_mode(qtbot):
    overlay = OverlayWindow(on_cancel=lambda: None)
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))
    overlay._bubble.clicked.emit()  # -> idle bubble

    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=2))

    assert overlay._bubble._idle is False
    assert not overlay._showing_idle_bubble


def test_idle_bubble_survives_a_realistic_synchronous_on_cancel(qtbot):
    """on_cancel in production (bootstrap's request_cancel -> controller.cancel())
    synchronously re-enters apply_view_state(IDLE) before _on_bubble_clicked
    returns -- a no-op on_cancel in a test doesn't exercise that reentrancy.
    Reproduces the real bug: the idle bubble appeared and then instantly
    vanished on every click, because on_cancel's synchronous IDLE callback
    ran before the idle-bubble flag was set."""
    overlay = OverlayWindow()

    def synchronous_cancel_like_bootstrap():
        overlay.apply_view_state(ViewState(state=AppState.IDLE, operation_id=99))

    overlay._on_cancel = synchronous_cancel_like_bootstrap
    qtbot.addWidget(overlay)
    overlay.apply_view_state(ViewState(state=AppState.CAPTURING, operation_id=1))

    overlay._bubble.clicked.emit()

    assert overlay.isVisible()
    assert overlay._bubble.isVisible()
    assert overlay._showing_idle_bubble
