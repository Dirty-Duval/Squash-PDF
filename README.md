# Squash - PDF Compressor

**Simple, user-friendly PDF compression tool for Windows.** Drop in PDFs, pick a quality, get smaller files. Everything runs locally with the bundled Ghostscript; nothing is uploaded.

## Features

- **Drag, drop, compress**: drop files or folders anywhere on the window, or use Add Files / Add Folder
- **Three presets plus your own**: Small (72 DPI), Medium (150 DPI), High Quality (300 DPI, keeps original colours), and custom presets with per-preset colour handling (keep / RGB / grayscale)
- **Live progress and cancel**: page-by-page progress, speed and time remaining, and a Cancel button that stops cleanly without leaving half-written files
- **Clear results**: before/after bars per file, warnings when a PDF was already optimised, plain-language errors for damaged or password-protected files, and an Open Output Folder button
- **Your rules for output**: save next to the original or into a fixed folder, with a configurable file name pattern. Originals are never overwritten
- **History and statistics**: searchable history, 30-day trend and preset comparison charts
- **Dark / light / system theme**, remembered window size and last-used preset
- **Auto-update** from GitHub Releases (can be switched off)
- **100% local**: no cloud, no account, no telemetry

## Installation

### From Installer (Recommended)
1. Download the latest `SquashSetup-<version>.exe` from [Releases](https://github.com/Dirty-Duval/Squash-PDF/releases)
2. Run it and follow the wizard
3. Launch from the desktop shortcut or Start Menu

### From Source
```bash
git clone https://github.com/Dirty-Duval/Squash-PDF.git
cd Squash-PDF
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m squash
```

Running from source uses the Ghostscript copy in `ghostscript/bin` if present, otherwise any Ghostscript on your PATH.

## Requirements

- Windows 10 (64-bit) or Windows 11
- ~200 MB free disk space
- Administrator privileges for installation

## Usage

1. **Launch Squash**
2. **Add PDFs**: drag and drop, click the drop zone, or use Add Files / Add Folder
3. **Pick a quality**: Small, Medium, High Quality, or a custom preset (the description under the presets explains the trade-off)
4. **Compress Now**. Watch progress, or press Cancel to stop
5. **Review the results**, then Open Output Folder

The line under the presets always tells you where files will be written and how they will be named.

## Settings

- **Appearance**: System, Light or Dark
- **Output**: destination folder (same folder as the original by default) and file name pattern using `{filename}`, with a live example
- **Compression**: time limit per file (default 300 s)
- **Ghostscript**: use the bundled copy or point to your own installation
- **Logging & Privacy**: log level, Open Log Folder, startup update check, keep history

## Development

```bash
pip install -r requirements-dev.txt

pytest                                  # unit + integration tests (Ghostscript tests skip if absent)
pytest --cov=squash --cov-report=html   # with coverage
black src/ && flake8 src/               # format and lint
python test_integration.py              # quick environment check
```

### Project Structure
```
Squash/
├── src/squash/
│   ├── core/            # Ghostscript wrapper, compression engine, batch processor, presets
│   ├── gui/             # Main window, dialogs, settings, preset editor, history, results
│   ├── config/          # Settings persistence
│   └── utils/           # Filesystem, logging, history database, updater
├── src/tests/           # unit/ and integration/
├── assets/              # Icon and theme
├── ghostscript/         # Bundled Ghostscript (AGPL)
└── docs/                # User guide and API reference
```

### Building

The version is defined once in `src/squash/__init__.py`; the build scripts read it from there.

```bash
build_all.bat          # executable + installer
build_exe.bat          # PyInstaller -> dist\Squash\Squash.exe
build_installer.bat    # Inno Setup -> dist\installer\SquashSetup-<version>.exe
```

See [CHANGELOG.md](CHANGELOG.md) for what changed in each release.

## License

AGPL-3.0, see [LICENSE](LICENSE). Ghostscript is distributed under its own AGPL-3.0 license, see `ghostscript/LICENSE`.

## Acknowledgments

- **Ghostscript**: PDF processing engine
- **CustomTkinter**: GUI toolkit
- **tkinterdnd2**: drag-and-drop support

## Support

- [User Guide](docs/user_guide.md)
- [Report Issues](https://github.com/Dirty-Duval/Squash-PDF/issues)
