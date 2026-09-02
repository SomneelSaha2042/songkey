from __future__ import annotations

import logging
import logging.handlers

from songkey.app.paths import log_dir, log_file_path

MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def configure_logging() -> None:
    log_dir().mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file_path(), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger("songkey")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
