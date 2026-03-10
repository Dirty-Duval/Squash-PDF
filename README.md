# Squash PDF

**Compress PDFs instantly — 100% local, no cloud, no data sharing.**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)](https://github.com/Dirty-Duval/Squash-PDF/releases/latest)
[![Version](https://img.shields.io/badge/Version-2.1.0-green)](https://github.com/Dirty-Duval/Squash-PDF/releases/latest)

---

## Download

**[⬇ Download SquashSetup-2.1.0.exe](https://github.com/Dirty-Duval/Squash-PDF/releases/latest)**

> Windows 10/11 (64-bit) · ~36 MB installer · Includes everything, no extras needed

---

## Features

- **Drag and drop** — drop one or many PDFs straight onto the window
- **3 quality presets** — Small (72 DPI), Medium (150 DPI), High (300 DPI)
- **Batch processing** — compress multiple files in one go
- **Custom presets** — create, save, import, and export your own compression settings
- **File history** — searchable log of every compression with size savings
- **Auto-update** — checks for new versions on startup, installs with one click
- **Dark & light themes** — picks your system theme automatically
- **100% local** — Ghostscript runs on your machine, nothing is uploaded anywhere

---

## Installation

1. [Download the installer](https://github.com/Dirty-Duval/Squash-PDF/releases/latest)
2. Run `SquashSetup-2.1.0.exe` and follow the wizard
3. Launch **Squash PDF** from the Start Menu or Desktop shortcut

No additional software needed — Ghostscript 10.06.0 is bundled.

---

## Quick start

1. Open Squash PDF
2. Add files — drag and drop PDFs onto the window, or click **Add Files**
3. Choose a preset — **Small**, **Medium**, or **High Quality**
4. Click **Compress**
5. Compressed files are saved next to the originals (or in your chosen output folder)

---

## Requirements

- Windows 10 or Windows 11 (64-bit)
- ~100 MB free disk space
- Administrator privileges for installation

---

## Building from source

```bash
git clone https://github.com/Dirty-Duval/Squash-PDF.git
cd Squash-PDF
pip install -r requirements-dev.txt
python src/squash/main.py
```

Requires Python 3.11+ and Ghostscript 10.x installed separately when running from source.

---

## License

[AGPL-3.0](LICENSE) — free to use, modify, and distribute under the same license.
