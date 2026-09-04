"""Composition root. The only module that wires every concrete adapter
together; every other module depends on protocols or injected callables."""

from __future__ import annotations

import faulthandler
import gc
import logging
import os
import sys

faulthandler.enable()

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from songkey.app.controller import AppController
from songkey.app.errors import AppError
from songkey.app.logging_setup import configure_logging
from songkey.audio.wasapi import WasapiCapture
from songkey.platform.windows.hotkey import GlobalHotkey
from songkey.platform.windows.single_instance import SingleInstanceGuard
from songkey.recognition.models import Track
from songkey.recognition.shazam import ShazamRecognitionProvider
from songkey.runtime.worker import RecognitionWorker
from songkey.ui.overlay import OverlayWindow
from songkey.ui.tray import TrayApp

logger = logging.getLogger("songkey.bootstrap")


class _WorkerTrigger(QObject):
    """Lives on the main thread. Emitting either signal queues onto the
    worker thread because the connected worker slots have worker-thread
    affinity."""

    start_requested = Signal(int)
    cancel_requested = Signal(int)


class _ControllerBridge(QObject):
    """Lives on the main thread. Worker signals connect to these slots so
    Qt queues the delivery, guaranteeing the controller is only ever
    touched from the main thread."""

    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._controller = controller

    @Slot(int)
    def on_capture_complete(self, operation_id: int) -> None:
        self._controller.on_capture_complete(operation_id)

    @Slot(int)
    def on_no_audio(self, operation_id: int) -> None:
        self._controller.on_no_audio(operation_id)

    @Slot(int, object)
    def on_found(self, operation_id: int, track: Track) -> None:
        self._controller.on_found(operation_id, track)

    @Slot(int)
    def on_not_found(self, operation_id: int) -> None:
        self._controller.on_not_found(operation_id)

    @Slot(int, object)
    def on_failed(self, operation_id: int, error: AppError) -> None:
        self._controller.on_failed(operation_id, error)


def main() -> int:
    configure_logging()
    logger.info("SongKey starting")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    guard = SingleInstanceGuard()
    if not guard.acquire():
        logger.info("Another SongKey instance is already running; exiting.")
        return 0

    capture = WasapiCapture()
    provider = ShazamRecognitionProvider()
    worker = RecognitionWorker(capture, provider)
    thread = QThread()
    worker.moveToThread(thread)
    thread.start()

    trigger_bridge = _WorkerTrigger()
    trigger_bridge.start_requested.connect(worker.run_operation)
    trigger_bridge.cancel_requested.connect(worker.cancel)

    def schedule_timer(seconds: float, callback) -> None:
        QTimer.singleShot(int(seconds * 1000), callback)

    def on_view_state(view_state) -> None:
        logger.info("state=%s op=%s track=%s message=%s", view_state.state, view_state.operation_id, view_state.track, view_state.message)
        overlay.apply_view_state(view_state)

    def request_cancel() -> None:
        logger.info("cancel requested via bubble click")
        controller.cancel()

    overlay = OverlayWindow(on_cancel=request_cancel, on_trigger=lambda: request_trigger("bubble restart"))

    controller = AppController(
        schedule_timer=schedule_timer,
        start_operation=trigger_bridge.start_requested.emit,
        on_view_state=on_view_state,
        request_cancel=trigger_bridge.cancel_requested.emit,
    )

    bridge = _ControllerBridge(controller)
    worker.capture_complete.connect(bridge.on_capture_complete)
    worker.no_audio.connect(bridge.on_no_audio)
    worker.found.connect(bridge.on_found)
    worker.not_found.connect(bridge.on_not_found)
    worker.failed.connect(bridge.on_failed)

    def request_trigger(source: str) -> None:
        logger.info("trigger requested via %s", source)
        controller.trigger()

    tray = TrayApp(on_recognize=lambda: request_trigger("tray menu"), on_quit=lambda: request_shutdown())

    hotkey = GlobalHotkey(on_triggered=lambda: request_trigger("hotkey"))
    app.installNativeEventFilter(hotkey)
    try:
        hotkey.register()
    except AppError:
        logger.warning("Hotkey registration failed", exc_info=True)
        tray.notify_warning("Ctrl + Alt + S is already in use. SongKey is running, but recognition is disabled.")

    shutdown_started = False

    def request_shutdown() -> None:
        nonlocal shutdown_started, tray, overlay, hotkey, worker, thread, capture, provider, bridge, trigger_bridge, controller, guard
        if shutdown_started:
            return
        shutdown_started = True

        logger.info("SongKey shutting down")
        hotkey.close()
        thread.requestInterruption()
        thread.quit()
        thread.wait(2000)
        capture.close()
        guard.release()
        tray.hide()
        overlay.hide()
        # Explicitly, deterministically drop every QObject-wrapping local
        # now, while the Qt event loop is still alive and healthy, rather
        # than leaving CPython's stack-frame teardown (after app.exec()
        # returns) to destroy them in whatever order it happens to pick.
        # Reference cycles between these objects (e.g. tray's Quit action
        # holding this closure, which closes back over tray) mean that
        # order is not guaranteed, and destroying a QWidget-derived object
        # after QApplication has begun tearing down segfaults intermittently
        # -- reproduced repeatedly during Milestone 2 testing (~30-50% of
        # Quit attempts) and fixed by this explicit teardown.
        del tray, overlay, hotkey, worker, thread, capture, provider, bridge, trigger_bridge, controller, guard
        gc.collect()
        app.processEvents()
        app.quit()

    auto_quit_seconds = os.environ.get("SONGKEY_AUTO_QUIT_SECONDS")
    if auto_quit_seconds:
        QTimer.singleShot(int(float(auto_quit_seconds) * 1000), request_shutdown)

    tray.show()
    exit_code = app.exec()
    request_shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
