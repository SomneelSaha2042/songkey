from __future__ import annotations

import math

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

CANVAS_SIZE = 96
ORB_DIAMETER = 64
PULSE_DURATION_MS = 900


class BubbleWidget(QWidget):
    """The listening/recognizing orb: a soft glow with a pulsing (listening)
    or rotating-arc (recognizing) animation, drawn entirely with QPainter --
    no image assets. Clickable: a misclicked trigger should be easy to
    back out of, so a click emits `clicked` for the overlay to wire to
    cancellation rather than silently swallowing the input."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(CANVAS_SIZE, CANVAS_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._pulse = 0.0
        self._rotation = 0.0
        self._recognizing = False

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
        self.update()

    pulse = Property(float, get_pulse, set_pulse)

    def get_rotation(self) -> float:
        return self._rotation

    def set_rotation(self, value: float) -> None:
        self._rotation = value
        self.update()

    rotation = Property(float, get_rotation, set_rotation)

    def start_listening(self) -> None:
        self._recognizing = False
        self._rotation_animation.stop()
        self._pulse_animation.start()

    def start_recognizing(self) -> None:
        self._recognizing = True
        self._pulse_animation.stop()
        self._pulse = 0.6
        self._rotation_animation.start()

    def stop(self) -> None:
        self._pulse_animation.stop()
        self._rotation_animation.stop()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        base_radius = ORB_DIAMETER / 2

        # Outer glow: radial gradient, breathing with the pulse.
        glow_radius = base_radius + 8 + 6 * self._pulse
        glow = QRadialGradient(center, glow_radius)
        glow.setColorAt(0.0, QColor(90, 170, 255, int(90 + 60 * self._pulse)))
        glow.setColorAt(1.0, QColor(90, 170, 255, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, glow_radius, glow_radius)

        # Inner circle.
        inner = QRadialGradient(center, base_radius)
        inner.setColorAt(0.0, QColor(120, 190, 255, 210))
        inner.setColorAt(1.0, QColor(70, 140, 235, 190))
        painter.setBrush(inner)
        painter.drawEllipse(center, base_radius, base_radius)

        if self._recognizing:
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
        start_angle = int(-self._rotation * 16)
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
            phase = self._pulse * 2 * math.pi + i * 0.9
            height = base_radius * (0.25 + 0.2 * abs(math.sin(phase)))
            x = start_x + i * spacing
            path.moveTo(x, center.y() - height)
            path.lineTo(x, center.y() + height)
        painter.drawPath(path)
