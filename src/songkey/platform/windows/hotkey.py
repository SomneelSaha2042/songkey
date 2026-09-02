from __future__ import annotations

import ctypes
import ctypes.wintypes
from collections.abc import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, Qt
from PySide6.QtWidgets import QWidget

from songkey.app.errors import AppError, AppErrorCode

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_S = 0x53
WM_HOTKEY = 0x0312
HOTKEY_ID = 1


class _HiddenMessageWindow(QWidget):
    """A never-shown top-level widget that exists only to force creation of
    a native HWND that RegisterHotKey can bind to."""

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.setFixedSize(0, 0)


class GlobalHotkey(QAbstractNativeEventFilter):
    """Registers Ctrl+Alt+S system-wide via User32.RegisterHotKey and routes
    WM_HOTKEY through a Qt native event filter. Registration/unregistration
    happen on the GUI thread because the window handle belongs to it."""

    def __init__(self, on_triggered: Callable[[], None]) -> None:
        super().__init__()
        self._on_triggered = on_triggered
        self._window = _HiddenMessageWindow()
        self._window.winId()  # force native HWND creation
        self._hwnd = int(self._window.winId())
        self._registered = False

    def register(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        ok = user32.RegisterHotKey(self._hwnd, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_S)
        if not ok:
            error_code = ctypes.get_last_error()
            raise AppError(AppErrorCode.HOTKEY_UNAVAILABLE, f"RegisterHotKey failed, GetLastError={error_code}")
        self._registered = True

    def unregister(self) -> None:
        if self._registered:
            ctypes.windll.user32.UnregisterHotKey(self._hwnd, HOTKEY_ID)
            self._registered = False

    def nativeEventFilter(self, event_type: QByteArray | bytes, message: int) -> tuple[bool, int]:
        if event_type != b"windows_generic_MSG":
            return False, 0

        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            self._on_triggered()
        return False, 0
