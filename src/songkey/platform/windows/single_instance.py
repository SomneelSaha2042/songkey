from __future__ import annotations

import ctypes
from typing import Self

MUTEX_NAME = r"Local\SongKeyDesktopApp"
ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """Per-user named Windows mutex. Prevents duplicate tray icons and
    duplicate hotkey registration attempts without another dependency."""

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self._name = name
        self._handle: int | None = None

    def acquire(self) -> bool:
        """Returns True if this process is the sole instance, False if
        another instance already holds the mutex."""
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, self._name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        self._handle = handle
        already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        return not already_running

    def release(self) -> None:
        if self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
