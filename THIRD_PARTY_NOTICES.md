# Third-Party Notices

SongKey is built with the following open-source software. This file is an
engineering-level summary, not legal advice — review the linked license
texts directly before any binary redistribution.

| Package | License | Notes |
| --- | --- | --- |
| [PySide6](https://pypi.org/project/PySide6/) (Qt for Python) | LGPLv3 (commercial/GPL also available) | Used dynamically; not modified. |
| [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | Apache-2.0 | WASAPI loopback capture. |
| [ShazamIO](https://github.com/shazamio/ShazamIO) | MIT | Unofficial client for a reverse-engineered Shazam API — see [design doc §7.4](docs/design.md#74-provider-risk) for the risk analysis. |
| [numpy](https://numpy.org/) | BSD-3-Clause | Pulled in transitively by ShazamIO; used for silence-detection metrics. |
| PyInstaller (build-time only, not yet wired into this repo) | GPL-2.0-or-later, with an exception permitting distribution of the bundled application | Will apply once Milestone 4 packaging lands. |
| pytest, pytest-qt, pytest-cov, ruff, mypy | Various OSI licenses (MIT/Apache-2.0) | Development-only; not distributed with the app. |

SongKey does not use, redistribute, or claim affiliation with any Shazam
trademark or official Shazam SDK. See `docs/design.md` §7.4 and §14 for the
full analysis this project was built against.
