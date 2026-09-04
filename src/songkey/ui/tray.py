from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


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
    """Tray icon, menu, and hotkey-conflict notifications. Result display
    lives in the overlay window (ui/overlay.py) instead."""

    def __init__(self, on_recognize: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._icon = QSystemTrayIcon(_make_icon())
        self._icon.setToolTip("SongKey")

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

    def notify_warning(self, text: str) -> None:
        self._icon.showMessage("SongKey", text, QSystemTrayIcon.MessageIcon.Warning, 5000)
