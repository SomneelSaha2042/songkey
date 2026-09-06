from __future__ import annotations

import math

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QGraphicsBlurEffect, QWidget

ORB_DIAMETER = 64
PULSE_DURATION_MS = 900
GLOW_BLUR_RADIUS = 18
# Room around the orb for the glow's blur to bleed into -- without it, the
# blur gets clipped at the window edge, since the overlay window is sized
# to exactly match this widget (see ui/overlay.py's _place()).
CANVAS_SIZE = 160


class _GlowLayer(QWidget):
    """Bottom layer: a soft-edged circle with a real QGraphicsBlurEffect
    applied, instead of the QRadialGradient approximation this replaced --
    a gradient can only fake a blur's falloff, an actual blur reads softer
    and closer to the design reference at this widget's small size."""

    def __init__(self, bubble: BubbleWidget) -> None:
        super().__init__(bubble)
        self._bubble = bubble
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        blur = QGraphicsBlurEffect(self)
        blur.setBlurRadius(GLOW_BLUR_RADIUS)
        self.setGraphicsEffect(blur)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        base_radius = ORB_DIAMETER / 2
        idle = self._bubble._idle
        pulse = self._bubble._pulse

        glow_alpha = 55 if idle else int(90 + 60 * pulse)
        glow_radius = base_radius + 8 + (0 if idle else 6 * pulse)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(90, 170, 255, glow_alpha))
        painter.drawEllipse(center, glow_radius, glow_radius)


class _OrbLayer(QWidget):
    """Top layer: the crisp inner circle plus the wave/arc glyph. Kept sharp
    (no blur effect) so the glow underneath doesn't smear the parts meant to
    read clearly at a glance."""

    def __init__(self, bubble: BubbleWidget) -> None:
        super().__init__(bubble)
        self._bubble = bubble
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        base_radius = ORB_DIAMETER / 2
        bubble = self._bubble

        inner = QRadialGradient(center, base_radius)
        if bubble._idle:
            inner.setColorAt(0.0, QColor(140, 150, 165, 150))
            inner.setColorAt(1.0, QColor(90, 100, 115, 130))
        else:
            inner.setColorAt(0.0, QColor(120, 190, 255, 210))
            inner.setColorAt(1.0, QColor(70, 140, 235, 190))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(inner)
        painter.drawEllipse(center, base_radius, base_radius)

        if bubble._idle:
            return
        if bubble._recognizing:
            self._paint_recognizing_arc(painter, center, base_radius)
        else:
            self._paint_wave_glyph(painter, center, base_radius)

    def _paint_recognizing_arc(self, painter: QPainter, center, base_radius: float) -> None:
        pen = QPen(QColor(255, 255, 255, 230))
        pen.setWidthF(3.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(center.x() - base_radius + 6, center.y() - base_radius + 6, (base_radius - 6) * 2, (base_radius - 6) * 2)
        start_angle = int(-self._bubble._rotation * 16)
        span_angle = 90 * 16
        painter.drawArc(rect, start_angle, span_angle)

    def _paint_wave_glyph(self, painter: QPainter, center, base_radius: float) -> None:
        pen = QPen(QColor(255, 255, 255, 220))
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        path = QPainterPath()
        bar_count = 4
        spacing = base_radius * 0.5
        start_x = center.x() - spacing * (bar_count - 1) / 2
        for i in range(bar_count):
            phase = self._bubble._pulse * 2 * math.pi + i * 0.9
            height = base_radius * (0.25 + 0.2 * abs(math.sin(phase)))
            x = start_x + i * spacing
            path.moveTo(x, center.y() - height)
            path.lineTo(x, center.y() + height)
        painter.drawPath(path)


class BubbleWidget(QWidget):
    """The listening/recognizing orb: a soft glow (blurred) with a pulsing
    (listening) or rotating-arc (recognizing) animation. Holds the shared
    animatable state and dispatches repaints to its two child layers
    (_GlowLayer behind, _OrbLayer in front) rather than painting itself --
    a QGraphicsEffect attaches to a widget, so the blurred glow has to be
    its own widget, separate from the crisp orb on top of it. Clickable: a
    misclicked trigger should be easy to back out of, so a click emits
    `clicked` for the overlay to wire to cancellation rather than silently
    swallowing the input."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(CANVAS_SIZE, CANVAS_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._pulse = 0.0
        self._rotation = 0.0
        self._recognizing = False
        self._idle = False

        self._glow = _GlowLayer(self)
        self._glow.setGeometry(0, 0, CANVAS_SIZE, CANVAS_SIZE)
        self._orb = _OrbLayer(self)
        self._orb.setGeometry(0, 0, CANVAS_SIZE, CANVAS_SIZE)

        self._pulse_animation = QPropertyAnimation(self, b"pulse")
        self._pulse_animation.setDuration(PULSE_DURATION_MS)
        self._pulse_animation.setStartValue(0.0)
        self._pulse_animation.setEndValue(1.0)
        self._pulse_animation.setLoopCount(-1)

        self._rotation_animation = QPropertyAnimation(self, b"rotation")
        self._rotation_animation.setDuration(1800)
        self._rotation_animation.setStartValue(0.0)
        self._rotation_animation.setEndValue(360.0)
        self._rotation_animation.setLoopCount(-1)

    def get_pulse(self) -> float:
        return self._pulse

    def set_pulse(self, value: float) -> None:
        self._pulse = value
        self._glow.update()
        self._orb.update()

    pulse = Property(float, get_pulse, set_pulse)

    def get_rotation(self) -> float:
        return self._rotation

    def set_rotation(self, value: float) -> None:
        self._rotation = value
        self._orb.update()

    rotation = Property(float, get_rotation, set_rotation)

    def start_listening(self) -> None:
        self._idle = False
        self._recognizing = False
        self._rotation_animation.stop()
        self._pulse_animation.start()

    def start_recognizing(self) -> None:
        self._idle = False
        self._recognizing = True
        self._pulse_animation.stop()
        self._pulse = 0.6
        self._rotation_animation.start()

    def start_idle(self) -> None:
        """Dim, static orb shown after a cancel-click: click again to
        restart listening, or move away to dismiss it."""
        self._idle = True
        self._recognizing = False
        self._pulse_animation.stop()
        self._rotation_animation.stop()
        self._pulse = 0.0
        self._glow.update()
        self._orb.update()

    def stop(self) -> None:
        self._idle = False
        self._pulse_animation.stop()
        self._rotation_animation.stop()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
