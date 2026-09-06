from __future__ import annotations

from songkey.recognition.models import Track
from songkey.ui.tray import HISTORY_LIMIT, TrayApp

TRACK_A = Track(provider_id="1", title="Song A", artist="Artist A", cover_url=None, provider_url="https://shazam.example/1")
TRACK_B = Track(provider_id="2", title="Song B", artist="Artist B", cover_url=None, provider_url=None)


def _entry_labels(tray: TrayApp) -> list[str]:
    return [action.text() for action in tray._history_menu.actions() if action.menu() is not None]


def test_tray_icon_loads_the_real_app_icon(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)

    icon = tray._icon.icon()
    assert not icon.isNull()
    assert icon.availableSizes()


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


def test_clicking_history_actions_opens_the_correct_url_not_the_checked_bool(qapp, monkeypatch):
    """Regression test: QAction.trigger() (like a real click) emits
    triggered(bool), and a lambda with a default parameter Qt can fill
    (`lambda url=x: ...`) gets that bool passed positionally, silently
    clobbering the captured value -- every history action opened `True`
    instead of its URL until fixed. .trigger() reproduces this; asserting
    only the menu's labels (as the other tests here do) does not."""
    opened = []
    monkeypatch.setattr("songkey.ui.tray.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)
    tray.update_history([TRACK_A])
    entry_menu = next(a for a in tray._history_menu.actions() if a.menu() is not None).menu()

    spotify_action = next(a for a in entry_menu.actions() if a.text() == "Open Spotify")
    spotify_action.trigger()
    youtube_action = next(a for a in entry_menu.actions() if a.text() == "Open YouTube")
    youtube_action.trigger()
    shazam_action = next(a for a in entry_menu.actions() if a.text() == "Open Shazam")
    shazam_action.trigger()

    # QUrl.toString() decodes percent-encoding back to plain text.
    assert opened == [
        "https://open.spotify.com/search/Artist A Song A",
        "https://www.youtube.com/results?search_query=Artist A Song A",
        "https://shazam.example/1",
    ]


def test_clicking_copy_action_sets_the_correct_clipboard_text(qapp):
    tray = TrayApp(on_recognize=lambda: None, on_quit=lambda: None)
    tray.update_history([TRACK_A])
    entry_menu = next(a for a in tray._history_menu.actions() if a.menu() is not None).menu()

    copy_action = next(a for a in entry_menu.actions() if a.text() == "Copy")
    copy_action.trigger()

    assert qapp.clipboard().text() == "Artist A — Song A"
