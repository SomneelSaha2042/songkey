# Release checklist

Run through this before tagging a release. See `docs/design.md` §13.7
(packaging smoke test), §13.8 (manual acceptance matrix), and §13.9
(quality gates) for the full rationale behind each item.

## Build

- [ ] `python -m pytest -m "not hardware and not live"` passes.
- [ ] `python -m pytest -m hardware` passes on real Windows audio hardware
      (needs a working speaker/headphone output).
- [ ] `ruff check src tests scripts` and `mypy src` are clean.
- [ ] `pyinstaller packaging\songkey.spec --clean --noconfirm` completes
      with no new hidden-import warnings beyond the known-harmless
      `tzdata` one (pulled in transitively, unused by SongKey).
- [ ] `dist\SongKey\_internal\assets\icons\songkey.ico` exists (icon
      actually bundled, not silently dropped).

## Packaging smoke test

Ideally on a clean Windows profile or Windows Sandbox — a dev machine
with Python already installed can't fully confirm "runs with no Python
installed", only that the frozen exe launches and doesn't reach for the
dev venv.

- [ ] Launch `dist\SongKey\SongKey.exe` directly (not via `python -m`).
      Tray icon appears within a couple seconds.
- [ ] Launch it again while the first is still running: second process
      exits immediately, no duplicate tray icon, log shows "Another
      SongKey instance is already running".
- [ ] Press `Ctrl+Alt+S` (or use the tray menu) with music playing:
      bubble → arc → a real result card with a correct match.
- [ ] Disconnect the network mid-flow: lands on the red error card
      ("You're offline"), no crash.
- [ ] Quit from the tray: process exits cleanly (exit code 0), no
      orphaned process, log shows "SongKey shutting down" with nothing
      after it.
- [ ] Inspect `%LOCALAPPDATA%\SongKey\logs\songkey.log`: no PCM, WAV
      bytes, fingerprints, or raw provider responses anywhere in it.

## Distribution

- [ ] Zip `dist\SongKey\` (the whole folder, not just the .exe) as
      `SongKey-vX.Y.Z-win64.zip`.
- [ ] On a separate machine (or a fresh user profile), unzip and launch
      `SongKey.exe` directly from the extracted folder — confirms the
      onedir layout doesn't depend on anything from the build machine.
- [ ] Tag the release in git; note in the release description that the
      binary is unsigned (see `docs/design.md` §14 — code signing is
      out of scope, Windows SmartScreen may warn on first run).
