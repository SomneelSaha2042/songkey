"""Regression guard for a real, repeatedly-reproduced Milestone 2 bug:
tearing down tray + hotkey + worker QThread + WASAPI capture on Quit
segfaulted 30-50% of the time (Windows access violation, no Python frame --
CPython's implicit stack-frame teardown destroying QObject-wrapping locals
in an unpredictable order after app.exec() returned, racing Qt's own
teardown). Fixed in bootstrap.request_shutdown() by explicitly,
deterministically dropping every such reference while the Qt event loop is
still alive, before app.quit(). Requires real Windows audio hardware
(WasapiCapture opens a real PyAudio host), so this is opt-in.

Run: python -m pytest -m hardware tests/hardware/test_shutdown_stability.py
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

RUNS = 15
PER_RUN_TIMEOUT_SECONDS = 10


@pytest.mark.hardware
def test_repeated_launch_and_auto_quit_never_crashes():
    env = dict(os.environ, SONGKEY_AUTO_QUIT_SECONDS="1.5")
    failures = []

    for i in range(RUNS):
        result = subprocess.run(
            [sys.executable, "-m", "songkey"],
            env=env,
            capture_output=True,
            timeout=PER_RUN_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            failures.append((i, result.returncode, result.stderr.decode(errors="replace")[-500:]))

    assert not failures, f"{len(failures)}/{RUNS} runs crashed or exited non-zero: {failures}"
