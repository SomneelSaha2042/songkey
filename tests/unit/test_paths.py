from __future__ import annotations

import sys

from songkey.app.paths import icon_path


def test_icon_path_points_at_an_existing_file():
    path = icon_path()

    assert path.name == "songkey.ico"
    assert path.exists()


def test_icon_path_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    path = icon_path()

    assert path == tmp_path / "assets" / "icons" / "songkey.ico"
