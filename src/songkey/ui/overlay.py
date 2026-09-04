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

    def __init__(self, on_cancel: Callable[[], None] | None = None) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._bubble = BubbleWidget(self)
        self._bubble.hide()
        if on_cancel is not None:
            self._bubble.clicked.connect(on_cancel)
        self._card = ResultCardWidget(self)
        self._card.hide()

        self._pending_hide = False

    def apply_view_state(self, view_state: ViewState) -> None:
        state = view_state.state

        if state is AppState.IDLE:
            if self._card.isVisible() and self._card.underMouse():
                self._pending_hide = True
                return
            self._hide_all()
            return

        self._pending_hide = False

        if state in _BUBBLE_STATES:
            self._show_bubble(state)
        else:
            self._show_card(view_state)

    def leaveEvent(self, event) -> None:
        if self._pending_hide:
            self._pending_hide = False
            self._hide_all()
        super().leaveEvent(event)

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
