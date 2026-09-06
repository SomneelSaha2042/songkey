from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from songkey.app.state import AppState, ViewState
from songkey.recognition import actions
from songkey.recognition.models import Track

CARD_WIDTH = 360
CARD_HEIGHT = 96
# Room around the visible card for the drop shadow to bleed into -- without
# it, the shadow gets clipped at the window edge, since the overlay window
# is sized to exactly match this widget (see ui/overlay.py's _place()).
CARD_MARGIN = 32
COVER_SIZE = 64
COVER_FETCH_TIMEOUT_MS = 4000
COVER_MAX_BYTES = 2_000_000

_TINTS: dict[AppState, QColor] = {
    AppState.FOUND: QColor(40, 44, 52, 235),
    AppState.NOT_FOUND: QColor(120, 90, 20, 235),
    AppState.NO_AUDIO: QColor(50, 50, 55, 220),
    AppState.ERROR: QColor(120, 30, 30, 235),
}

_LABELS: dict[AppState, str] = {
    AppState.NOT_FOUND: "No match found",
    AppState.NO_AUDIO: "No audio is playing",
}


class ResultCardWidget(QWidget):
    """Renders the terminal states: the full Found card (cover, title,
    artist, actions) or a compact tinted status card (no match / no audio /
    error). Accepts mouse input -- unlike the listening bubble -- because it
    contains clickable actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(CARD_WIDTH + 2 * CARD_MARGIN, CARD_HEIGHT + 2 * CARD_MARGIN)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._tint = QColor(40, 44, 52, 235)
        self._network = QNetworkAccessManager(self)
        self._cover_pixmap: QPixmap | None = None
        self._pending_cover_reply: QNetworkReply | None = None

        self._cover_label = QLabel(self)
        self._cover_label.setFixedSize(COVER_SIZE, COVER_SIZE)

        self._title_label = QLabel(self)
        self._title_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        self._artist_label = QLabel(self)
        self._artist_label.setStyleSheet("color: rgba(255,255,255,190); font-size: 12px;")

        self._status_label = QLabel(self)
        self._status_label.setStyleSheet("color: white; font-size: 13px;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_column = QVBoxLayout()
        text_column.addStretch(1)
        text_column.addWidget(self._title_label)
        text_column.addWidget(self._artist_label)
        text_column.addStretch(1)

        self._action_buttons: list[QPushButton] = []
        actions_row = QHBoxLayout()
        actions_row.setSpacing(4)
        for label in ("Shazam", "Spotify", "YouTube", "Copy"):
            button = QPushButton(label, self)
            button.setStyleSheet(
                "QPushButton { color: white; background: rgba(255,255,255,30); border: none;"
                " border-radius: 4px; padding: 3px 6px; font-size: 11px; }"
                "QPushButton:hover { background: rgba(255,255,255,55); }"
            )
            actions_row.addWidget(button)
            self._action_buttons.append(button)
        text_column.addLayout(actions_row)

        self._found_layout = QHBoxLayout()
        self._found_layout.setContentsMargins(16, 12, 16, 12)
        self._found_layout.setSpacing(12)
        self._found_layout.addWidget(self._cover_label)
        self._found_layout.addLayout(text_column, 1)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(CARD_MARGIN, CARD_MARGIN, CARD_MARGIN, CARD_MARGIN)
        self._root_layout.addLayout(self._found_layout)
        self._root_layout.addWidget(self._status_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(CARD_MARGIN, CARD_MARGIN, CARD_WIDTH, CARD_HEIGHT), 14, 14)
        painter.fillPath(path, self._tint)

    def apply_view_state(self, view_state: ViewState, action_urls: dict[str, str | None] | None = None) -> None:
        state = view_state.state
        self._tint = _TINTS.get(state, QColor(40, 44, 52, 235))

        is_found = state is AppState.FOUND and view_state.track is not None
        for widget in (self._cover_label, self._title_label, self._artist_label, *self._action_buttons):
            widget.setVisible(is_found)
        self._status_label.setVisible(not is_found)

        if is_found:
            track = view_state.track
            assert track is not None
            self._title_label.setText(track.title)
            self._artist_label.setText(track.artist)
            self._render_fallback_cover()
            self._fetch_cover(track.cover_url)
            self._wire_actions(track, action_urls or {})
        else:
            text = (view_state.message if state is AppState.ERROR else _LABELS.get(state, "")) or ""
            self._status_label.setText(text)

        self.update()

    def _wire_actions(self, track: Track, action_urls: dict[str, str | None]) -> None:
        shazam_button, spotify_button, youtube_button, copy_button = self._action_buttons

        shazam_url = action_urls.get("shazam", actions.shazam_url(track))
        shazam_button.setVisible(bool(shazam_url))
        self._rebind(shazam_button, lambda: self._open(shazam_url))

        spotify_url = action_urls.get("spotify", actions.spotify_search_url(track))
        self._rebind(spotify_button, lambda: self._open(spotify_url))

        youtube_url = action_urls.get("youtube", actions.youtube_search_url(track))
        self._rebind(youtube_button, lambda: self._open(youtube_url))

        self._rebind(copy_button, lambda: self._copy(actions.copy_text(track)))

    @staticmethod
    def _rebind(button: QPushButton, callback: Callable[[], None]) -> None:
        if button.property("_songkey_bound"):
            button.clicked.disconnect()
        button.setProperty("_songkey_bound", True)
        button.clicked.connect(callback)

    def _open(self, url: str | None) -> None:
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _copy(self, text: str) -> None:
        QApplication.clipboard().setText(text)

    def _render_fallback_cover(self) -> None:
        pixmap = QPixmap(QSize(COVER_SIZE, COVER_SIZE))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, COVER_SIZE, COVER_SIZE), 8, 8)
        painter.fillPath(path, QColor(90, 170, 255, 220))
        painter.end()
        self._cover_label.setPixmap(pixmap)

    def _fetch_cover(self, cover_url: str | None) -> None:
        if self._pending_cover_reply is not None:
            self._pending_cover_reply.abort()
            self._pending_cover_reply = None

        if not cover_url:
            return

        request = QNetworkRequest(QUrl(cover_url))
        request.setMaximumRedirectsAllowed(3)
        request.setTransferTimeout(COVER_FETCH_TIMEOUT_MS)
        reply = self._network.get(request)
        self._pending_cover_reply = reply
        reply.finished.connect(lambda: self._on_cover_fetched(reply))

    def _on_cover_fetched(self, reply: QNetworkReply) -> None:
        if reply is not self._pending_cover_reply:
            reply.deleteLater()
            return
        self._pending_cover_reply = None

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            data = reply.readAll()
            if data.size() > COVER_MAX_BYTES:
                return
            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                return
            scaled = pixmap.scaled(
                COVER_SIZE, COVER_SIZE, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            rounded = QPixmap(QSize(COVER_SIZE, COVER_SIZE))
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, COVER_SIZE, COVER_SIZE), 8, 8)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            self._cover_pixmap = rounded
            self._cover_label.setPixmap(rounded)
        finally:
            reply.deleteLater()
