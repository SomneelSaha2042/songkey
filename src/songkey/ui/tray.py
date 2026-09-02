from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from songkey.app.state import AppState, ViewState

# Milestone 2 stand-in for the Milestone 3 glow overlay: tray tooltip +
# balloon notifications, driven by the same ViewState the real overlay
# will consume later.
_DESCRIPTIONS = {
    AppState.IDLE: "idle",
    AppState.CAPTURING: "listening…",
    AppState.RECOGNIZING: "recognizing…",
}


def _make_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(90, 170, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)


class TrayApp:
    def __init__(self, on_recognize: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._icon = QSystemTrayIcon(_make_icon())
        self._icon.setToolTip("SongKey — idle")

        menu = QMenu()
        recognize_action = menu.addAction("Recognize now")
        recognize_action.triggered.connect(on_recognize)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(on_quit)
        self._icon.setContextMenu(menu)

    def show(self) -> None:
        self._icon.show()

    def hide(self) -> None:
        self._icon.hide()

    def render(self, view_state: ViewState) -> None:
        if view_state.state in _DESCRIPTIONS:
            self._icon.setToolTip(f"SongKey — {_DESCRIPTIONS[view_state.state]}")
            return

        if view_state.state is AppState.FOUND and view_state.track is not None:
            text = f"{view_state.track.artist} — {view_state.track.title}"
            self._icon.setToolTip(f"SongKey — {text}")
            self._icon.showMessage("SongKey", text, QSystemTrayIcon.MessageIcon.Information, 4000)
        elif view_state.state is AppState.NOT_FOUND:
            self._icon.setToolTip("SongKey — no match")
            self._icon.showMessage("SongKey", "No match found", QSystemTrayIcon.MessageIcon.Information, 2500)
        elif view_state.state is AppState.NO_AUDIO:
            self._icon.setToolTip("SongKey — no audio")
            self._icon.showMessage("SongKey", "No audio is playing", QSystemTrayIcon.MessageIcon.Information, 2500)
        elif view_state.state is AppState.ERROR:
            text = view_state.message or "Something went wrong"
            self._icon.setToolTip(f"SongKey — {text}")
            self._icon.showMessage("SongKey", text, QSystemTrayIcon.MessageIcon.Warning, 4000)

    def notify_warning(self, text: str) -> None:
        self._icon.showMessage("SongKey", text, QSystemTrayIcon.MessageIcon.Warning, 5000)
