"""Renders assets/icons/songkey.svg's design (hand-kept in sync here, since
no SVG rasterizer is available in this environment) into a multi-resolution
Windows .ico using PySide6's QPainter, and writes the .ico bytes directly
(ICONDIR + PNG-compressed frames -- supported since Windows Vista) with no
external tool.

Design source of truth: assets/icons/design_handoff/README.md. Five
keycap-shaped bars over a dark rounded-square tile with a soft radial glow.
At 16/24px the five-bar group compresses too much to read, so those frames
drop the two shortest bars per the handoff's own guidance.

Run: python scripts/build_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QRadialGradient
from PySide6.QtWidgets import QApplication

REFERENCE_SIZE = 512
TILE_RADIUS_FRACTION = 112 / REFERENCE_SIZE

TILE_GRADIENT_CENTER = (0.30, 0.22)  # fraction of tile size
TILE_GRADIENT_STOPS = [
    (0.0, "#281e39"),
    (0.55, "#090715"),
    (1.0, "#010104"),
]
BORDER_COLOR = QColor(255, 255, 255, int(0.06 * 255))

GLOW_RADIUS_FRACTION = 150 / REFERENCE_SIZE  # centered on the tile
GLOW_COLOR = QColor(0xF7, 0x61, 0x9A)
GLOW_ALPHA = 0.45

# (x, y, width, height, color) in 512-reference coordinates.
BARS_FULL = [
    (119, 316, 42, 70, "#ff743f"),
    (177, 236, 42, 150, "#ff6b73"),
    (235, 156, 42, 230, "#fd6aa0"),
    (293, 236, 42, 150, "#ed6fc8"),
    (351, 316, 42, 70, "#d679eb"),
]
# Drop the two shortest bars for the smallest frames (README guidance) --
# the remaining three are already correctly positioned, no re-layout needed.
BARS_SIMPLIFIED = BARS_FULL[1:4]

ICO_SIZES_DETAILED = [256, 48, 32]
ICO_SIZES_SIMPLIFIED = [24, 16]


def render_icon(size: int, *, detailed: bool) -> QImage:
    scale = size / REFERENCE_SIZE
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    tile_rect = QRectF(0, 0, size, size)
    radius = TILE_RADIUS_FRACTION * size

    gradient = QRadialGradient(
        TILE_GRADIENT_CENTER[0] * size,
        TILE_GRADIENT_CENTER[1] * size,
        # Reaches the farthest corner from an off-center point, matching the
        # CSS `radial-gradient(circle at 30% 22%, ...)` default extent.
        ((size - TILE_GRADIENT_CENTER[0] * size) ** 2 + (size - TILE_GRADIENT_CENTER[1] * size) ** 2) ** 0.5,
    )
    for stop, color in TILE_GRADIENT_STOPS:
        gradient.setColorAt(stop, QColor(color))

    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile_rect, radius, radius)
    painter.fillPath(tile_path, gradient)

    if size >= 32:  # a 1px border disappears below this anyway
        painter.setPen(BORDER_COLOR)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = 0.5
        painter.drawRoundedRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset), radius - inset, radius - inset)

    if detailed:
        # Approximates the design's blurred glow circle with a native Qt
        # radial gradient (opaque center fading to transparent) rather than
        # a true Gaussian blur -- no blur primitive is available here, and a
        # soft radial falloff reads the same at icon size.
        glow_radius = GLOW_RADIUS_FRACTION * size
        glow = QRadialGradient(size / 2, size / 2, glow_radius)
        center_color = QColor(GLOW_COLOR)
        center_color.setAlphaF(GLOW_ALPHA)
        edge_color = QColor(GLOW_COLOR)
        edge_color.setAlphaF(0.0)
        glow.setColorAt(0.0, center_color)
        glow.setColorAt(1.0, edge_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(size / 2 - glow_radius, size / 2 - glow_radius, glow_radius * 2, glow_radius * 2))

    bars = BARS_FULL if detailed else BARS_SIMPLIFIED
    painter.setPen(Qt.PenStyle.NoPen)
    for x, y, w, h, color in bars:
        bar_rect = QRectF(x * scale, y * scale, w * scale, h * scale)
        bar_radius = (w * scale) / 2
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(bar_rect, bar_radius, bar_radius)

    painter.end()
    return image


def _to_png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data: QByteArray = buffer.data()
    return bytes(data)


def write_ico(frames: list[tuple[int, bytes]], path: Path) -> None:
    """ICO format: 6-byte ICONDIR, then one 16-byte ICONDIRENTRY per frame,
    then the concatenated PNG blobs. PNG-compressed frames are supported by
    every Windows version this app targets (Vista+)."""
    count = len(frames)
    header = struct.pack("<HHH", 0, 1, count)

    entries = b""
    offset = 6 + 16 * count
    for size, png_bytes in frames:
        dim = size if size < 256 else 0  # 0 means 256 in ICO format
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png_bytes), offset)
        offset += len(png_bytes)

    with open(path, "wb") as f:
        f.write(header)
        f.write(entries)
        for _size, png_bytes in frames:
            f.write(png_bytes)


def main() -> int:
    app = QApplication(sys.argv)  # QPainter/QImage need a QApplication

    frames: list[tuple[int, bytes]] = []
    for size in ICO_SIZES_DETAILED:
        frames.append((size, _to_png_bytes(render_icon(size, detailed=True))))
    for size in ICO_SIZES_SIMPLIFIED:
        frames.append((size, _to_png_bytes(render_icon(size, detailed=False))))

    out_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "songkey.ico"
    write_ico(frames, out_path)
    print(f"Wrote {out_path} ({len(frames)} frames: {[s for s, _ in frames]})")

    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
