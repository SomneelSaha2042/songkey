from __future__ import annotations

import pytest

from songkey.app.errors import AppError, AppErrorCode
from songkey.platform.windows.hotkey import GlobalHotkey


def test_register_then_unregister_succeeds(qapp):
    hotkey = GlobalHotkey(on_triggered=lambda: None)
    hotkey.register()
    hotkey.unregister()


def test_register_then_close_succeeds_and_frees_the_combo(qapp):
    hotkey = GlobalHotkey(on_triggered=lambda: None)
    hotkey.register()

    hotkey.close()

    other = GlobalHotkey(on_triggered=lambda: None)
    try:
        other.register()  # would raise HOTKEY_UNAVAILABLE if close() left it registered
    finally:
        other.unregister()


def test_registering_same_combo_twice_conflicts(qapp):
    first = GlobalHotkey(on_triggered=lambda: None)
    first.register()
    try:
        second = GlobalHotkey(on_triggered=lambda: None)
        with pytest.raises(AppError) as exc_info:
            second.register()
        assert exc_info.value.code is AppErrorCode.HOTKEY_UNAVAILABLE
    finally:
        first.unregister()
