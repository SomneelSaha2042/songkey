from __future__ import annotations

from songkey.app.paths import icon_path


def test_icon_path_points_at_an_existing_file():
    path = icon_path()

    assert path.name == "songkey.ico"
    assert path.exists()
