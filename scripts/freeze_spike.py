"""Milestone-0 spike: minimal script that imports PySide6, PyAudioWPatch,
and ShazamIO. Freeze this with PyInstaller to prove native extensions and
Qt plugins survive bundling before any UI work exists.

Freeze:
    pyinstaller scripts\\freeze_spike.py --onedir --noconfirm --clean

Run the frozen build:
    dist\\freeze_spike\\freeze_spike.exe
"""

from __future__ import annotations

import sys

import pyaudiowpatch as pyaudio
import shazamio
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication, QLabel


def main() -> int:
    print(f"PySide6 Qt version: {qVersion()}")
    print(f"shazamio module: {shazamio.__file__}")

    pa = pyaudio.PyAudio()
    try:
        device = pa.get_default_wasapi_loopback()
        print(f"Default WASAPI loopback: {device['name'] if device else None}")
    finally:
        pa.terminate()

    app = QApplication(sys.argv)
    label = QLabel("SongKey freeze spike OK")
    label.show()
    app.processEvents()
    print("Qt widget created and shown successfully.")
    label.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
