from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from songkey.app.paths import icon_path
from songkey.recognition import actions
from songkey.recognition.models import Track

HISTORY_LIMIT = 5


def _make_icon() -> QIcon:
    return QIcon(str(icon_path()))


def _open(url: str | None) -> None:
    if url:
        QDesktopServices.openUrl(QUrl(url))


class TrayApp:
    """Tray icon, menu, and hotkey-conflict notifications. Result display
    lives in the overlay window (ui/overlay.py) instead. The "Recent"
    submenu keeps an in-memory (not persisted across restarts) list of the
    last few recognized songs, each expanding to the same actions as the
    overlay's result card."""

    def __init__(
        self,
        on_recognize: Callable[[], None],
        on_quit: Callable[[], None],
        on_clear_history: Callable[[], None] | None = None,
    ) -> None:
        self._on_clear_history = on_clear_history
        self._icon = QSystemTrayIcon(_make_icon())
        self._icon.setToolTip("SongKey")

        menu = QMenu()
        recognize_action = menu.addAction("Recognize now")
        recognize_action.triggered.connect(on_recognize)
        self._history_menu = menu.addMenu("Recent")
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(on_quit)
        self._icon.setContextMenu(menu)

        self.update_history([])

    def show(self) -> None:
        self._icon.show()

    def hide(self) -> None:
        self._icon.hide()

    def notify_warning(self, text: str) -> None:
        self._icon.showMessage("SongKey", text, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def update_history(self, tracks: Sequence[Track]) -> None:
        self._history_menu.clear()

        if not tracks:
            empty_action = self._history_menu.addAction("No recent songs")
            empty_action.setEnabled(False)
        else:
            for track in tracks[:HISTORY_LIMIT]:
                self._add_history_entry(track)

        self._history_menu.addSeparator()
        clear_action = self._history_menu.addAction("Clear history")
        clear_action.setEnabled(bool(tracks))
        clear_action.triggered.connect(self._on_clear_history_clicked)

    def _on_clear_history_clicked(self) -> None:
        if self._on_clear_history is not None:
            self._on_clear_history()

    def _add_history_entry(self, track: Track) -> None:
        # Each call has its own local `track`/url variables -- a plain
        # zero-arg lambda closes over *this* call's values correctly (no
        # loop-variable late-binding risk here, since this isn't itself a
        # loop body). Deliberately not `lambda url=...: ...`: QAction's
        # triggered(bool) signal passes `checked` positionally into any
        # parameter a connected lambda accepts, silently clobbering a
        # "default" used for capture -- broke every action in this menu
        # (calls landed as _open(True)/setText(True)) until fixed.
        track_menu = self._history_menu.addMenu(f"{track.artist} — {track.title}")

        shazam_url = actions.shazam_url(track)
        if shazam_url:
            action = track_menu.addAction("Open Shazam")
            action.triggered.connect(lambda: _open(shazam_url))

        spotify_url = actions.spotify_search_url(track)
        spotify_action = track_menu.addAction("Open Spotify")
        spotify_action.triggered.connect(lambda: _open(spotify_url))

        youtube_url = actions.youtube_search_url(track)
        youtube_action = track_menu.addAction("Open YouTube")
        youtube_action.triggered.connect(lambda: _open(youtube_url))

        clipboard_text = actions.copy_text(track)
        copy_action = track_menu.addAction("Copy")
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(clipboard_text))
