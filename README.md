# SongKey

Press `Ctrl + Alt + S` to identify the song currently playing through your
Windows default audio output — no microphone, no API key, no subscription.

Design doc: see `docs/design.md` (not yet committed — pending Milestone 1).

## Status

Milestone 0 (feasibility spikes) complete:

- `scripts/diagnose_audio.py` — resolves the default WASAPI loopback device and captures/measures system audio.
- `scripts/smoke_recognize.py` — sends a WAV clip to ShazamIO and prints the recognized track.
- `scripts/freeze_spike.py` — proves PySide6 + PyAudioWPatch + shazamio-core survive a PyInstaller `--onedir` freeze.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Spikes

```powershell
python scripts\diagnose_audio.py --seconds 6 --save clip.wav
python scripts\smoke_recognize.py clip.wav
pyinstaller scripts\freeze_spike.py --onedir --noconfirm --clean
dist\freeze_spike\freeze_spike.exe
```
