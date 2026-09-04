from __future__ import annotations

from songkey.recognition.models import Track
from songkey.ui.tray import HISTORY_LIMIT, TrayApp

TRACK_A = Track(provider_id="1", title="Song A", artist="Artist A", cover_url=None, provider_url="https://shazam.example/1")
TRACK_B = Track(provider_id="2", title="Song B", artist="Artist B", cover_url=None, provider_url=None)


def _entry_labels(tray: TrayApp) -> list[str]:
    return [action.text() for action in tray._history_menu.actions() if action.menu() is not None]


def test_empty_history_shows_placeholder_and_disabled_clear(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)

    actions_list = tray._history_menu.actions()
    assert actions_list[0].text() == "No recent songs"
    assert not actions_list[0].isEnabled()
    clear_action = next(a for a in actions_list if a.text() == "Clear history")
    assert not clear_action.isEnabled()


def test_history_entries_show_artist_and_title(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)

    tray.update_history([TRACK_A, TRACK_B])

    assert _entry_labels(tray) == ["Artist A — Song A", "Artist B — Song B"]
    clear_action = next(a for a in tray._history_menu.actions() if a.text() == "Clear history")
    assert clear_action.isEnabled()


def test_history_is_capped_at_limit(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)
    tracks = [Track(provider_id=str(i), title=f"Song {i}", artist="Artist", cover_url=None, provider_url=None) for i in range(HISTORY_LIMIT + 3)]

    tray.update_history(tracks)

    assert len(_entry_labels(tray)) == HISTORY_LIMIT


def test_entry_without_provider_url_omits_shazam_action(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)

    tray.update_history([TRACK_B])  # no provider_url

    entry_menu = next(a for a in tray._history_menu.actions() if a.menu() is not None).menu()
    labels = [a.text() for a in entry_menu.actions()]
    assert "Open Shazam" not in labels
    assert labels == ["Open Spotify", "Open YouTube", "Copy"]


def test_entry_with_provider_url_includes_shazam_action(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)

    tray.update_history([TRACK_A])

    entry_menu = next(a for a in tray._history_menu.actions() if a.menu() is not None).menu()
    labels = [a.text() for a in entry_menu.actions()]
    assert labels == ["Open Shazam", "Open Spotify", "Open YouTube", "Copy"]


def test_clear_history_callback_invoked(qapp):
    cleared = []
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None, on_clear_history=lambda: cleared.append(True))
    tray.update_history([TRACK_A])

    clear_action = next(a for a in tray._history_menu.actions() if a.text() == "Clear history")
    clear_action.trigger()

    assert cleared == [True]
