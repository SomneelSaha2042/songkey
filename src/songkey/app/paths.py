from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "SongKey"


def log_dir() -> Path:
    return app_data_dir() / "logs"


def log_file_path() -> Path:
    return log_dir() / "songkey.log"


def icon_path() -> Path:
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base is not None:
        return Path(frozen_base) / "assets" / "icons" / "songkey.ico"
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "assets" / "icons" / "songkey.ico"
