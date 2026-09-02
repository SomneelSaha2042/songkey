from __future__ import annotations

import time

import pytest

from songkey.audio.wasapi import _run_with_timeout


def test_fast_function_returns_normally():
    assert _run_with_timeout(lambda: 42, timeout_seconds=1.0) == 42


def test_slow_function_raises_timeout_error_promptly():
    def slow() -> int:
        time.sleep(5.0)
        return 1

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        _run_with_timeout(slow, timeout_seconds=0.2)
    elapsed = time.monotonic() - started

    assert elapsed < 1.0  # must not block for the full 5s the helper thread is stuck in


def test_exception_inside_function_propagates():
    def boom() -> int:
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        _run_with_timeout(boom, timeout_seconds=1.0)
