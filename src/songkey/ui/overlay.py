from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget

from songkey.app.state import AppState, ViewState
from songkey.ui.bubble import BubbleWidget
from songkey.ui.result_card import ResultCardWidget

TOP_OFFSET = 72

_BUBBLE_STATES = frozenset({AppState.CAPTURING, AppState.RECOGNIZING})


class OverlayWindow(QWidget):
    """State-driven window shell: hosts the listening/recognizing bubble or
    the result/status card, positions itself on the monitor under the
    cursor, and never steals focus from the foreground app."""

    def __init__(
        self,
        on_cancel: Callable[[], None] | None = None,
        on_trigger: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._on_cancel = on_cancel
        self._on_trigger = on_trigger

        self._bubble = BubbleWidget(self)
        self._bubble.hide()
        self._bubble.clicked.connect(self._on_bubble_clicked)
        self._card = ResultCardWidget(self)
        self._card.hide()

        self._pending_hide = False
        # True between a cancel-click and either a restart-click or the
        # mouse leaving: the bubble stays up, dim and idle, as an easy way
        # to re-trigger without reaching for the hotkey or tray menu again.
        self._showing_idle_bubble = False

    def apply_view_state(self, view_state: ViewState) -> None:
        state = view_state.state

        if state is AppState.IDLE:
            if self._showing_idle_bubble:
                return  # a cancel-triggered IDLE we're deliberately holding onto
            if self._card.isVisible() and self._card.underMouse():
                self._pending_hide = True
                return
            self._hide_all()
            return

        self._pending_hide = False
        self._showing_idle_bubble = False

        if state in _BUBBLE_STATES:
            self._show_bubble(state)
        else:
            self._show_card(view_state)

    def leaveEvent(self, event) -> None:
        if self._showing_idle_bubble:
            self._showing_idle_bubble = False
            self._hide_all()
        if self._pending_hide:
            self._pending_hide = False
            self._hide_all()
        super().leaveEvent(event)

    def _on_bubble_clicked(self) -> None:
        if self._showing_idle_bubble:
            self._showing_idle_bubble = False
            self._hide_all()
            if self._on_trigger is not None:
                self._on_trigger()
        elif self._bubble.isVisible():
            # Enter idle mode *before* on_cancel(): on_cancel() runs the
            # controller synchronously, which reaches apply_view_state(IDLE)
            # before this function continues. Without the flag already set,
            # that call hides everything -- the idle bubble would appear
            # only to instantly vanish on every click.
            self._enter_idle_bubble()
            if self._on_cancel is not None:
                self._on_cancel()

    def _enter_idle_bubble(self) -> None:
        self._showing_idle_bubble = True
        # Deliberately do not reposition: the window is already exactly
        # where the bubble was when it was clicked. Calling move()/resize()
        # again mid-click (even to the identical geometry) was enough to
        # make Windows fire a spurious mouse-leave right after, dismissing
        # the idle bubble before the user could ever click it again.
        self._bubble.start_idle()

    def _show_bubble(self, state: AppState) -> None:
        self._card.hide()
        self._place(self._bubble.size())
        # Accepts clicks (to cancel a misclicked trigger) even though it
        # never accepts keyboard focus -- WindowDoesNotAcceptFocus on the
        # window flags already keeps the foreground app's focus untouched.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._bubble.show()
        if state is AppState.CAPTURING:
            self._bubble.start_listening()
        else:
            self._bubble.start_recognizing()
        self.show()

    def _show_card(self, view_state: ViewState) -> None:
        self._bubble.stop()
        self._bubble.hide()
        self._place(self._card.size())
        self._card.apply_view_state(view_state)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._card.show()
        self.show()

    def _hide_all(self) -> None:
        self._showing_idle_bubble = False
        self._bubble.stop()
        self.hide()
        self._bubble.hide()
        self._card.hide()

    def _place(self, size: QSize) -> None:
        self.resize(size)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        work_area = screen.availableGeometry()
        x = work_area.x() + (work_area.width() - size.width()) // 2
        y = work_area.y() + TOP_OFFSET
        self.move(x, y)
