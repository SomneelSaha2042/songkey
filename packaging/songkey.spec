# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SongKey. Produces a windowed, onedir build at
dist/SongKey/SongKey.exe. Build with:

    pyinstaller packaging\\songkey.spec --clean --noconfirm

onedir (not onefile) per docs/design.md 12.3: starts without unpacking to a
temp directory, keeps missing DLL/plugin failures inspectable, and is the
officially-supported default bundle shape.
"""

from pathlib import Path

repo_root = Path(SPECPATH).resolve().parent
icon_file = repo_root / "assets" / "icons" / "songkey.ico"

a = Analysis(
    [str(repo_root / "src" / "songkey" / "__main__.py")],
    pathex=[str(repo_root / "src")],
    binaries=[],
    datas=[
        (str(icon_file), "assets/icons"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SongKey",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="SongKey",
)
