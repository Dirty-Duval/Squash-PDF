# Continue Development Here

**Last Updated**: 2026-10-10
**Current Version**: 2.2.0 (in `src/squash/__init__.py`, the single source of truth)
**Status**: 2.2.0 revamp complete in this folder; not yet built, released or synced to the production repo.

## Where things stand

- Working copy: `Squash-Development` (this folder). It is not a git repository.
- Production mirror / release source: `../Squash-PDF` (GitHub `Dirty-Duval/Squash-PDF`). It still contains the 2.1.0 code.
- A copy of the 2.1.0 source as it was before the revamp was kept outside the project during the revamp session; the production folder is the lasting reference for 2.1.0.

## What 2.2.0 changed

See [CHANGELOG.md](CHANGELOG.md). Highlights: output folder / naming / timeout / log level settings actually work, cancel button, real page progress, friendly Ghostscript errors, no page auto-rotation, atomic output, duplicate presets with colour handling, windows sized to content, 148 tests.

## Verify

```bash
.venv\Scripts\activate                 # or: python -m venv .venv && pip install -r requirements-dev.txt
pytest                                 # 148 tests, includes real-Ghostscript integration tests
flake8 src/squash && black --check src
python -m squash                       # run the app
```

## Release checklist for 2.2.0

1. Copy `src/`, `assets/`, `docs/`, build scripts, `pyproject.toml`, `requirements*.txt`, `README*.md`, `CHANGELOG.md`, `squash.spec`, `squash.iss` into `../Squash-PDF` and commit there.
2. `build_all.bat` (needs PyInstaller in the active environment and Inno Setup 6). The installer picks up the version automatically.
3. Test the installer on this machine, ideally on a clean VM too.
4. Tag `v2.2.0` and upload `dist\installer\SquashSetup-2.2.0.exe` to a GitHub Release. The in-app updater looks for an asset whose name ends in `.exe` and contains `setup`.

## Known limits / ideas

- Per-file progress depends on Ghostscript printing `Page N` lines; a PDF with a single huge page shows no intermediate progress.
- Files are processed sequentially. Parallel Ghostscript processes would speed up large batches on multi-core machines.
- `docs/API_REFERENCE.md` describes the public modules; keep it in sync when changing signatures.

## Key files

- `src/squash/core/ghostscript.py`: subprocess wrapper, progress parsing, error classification, atomic output
- `src/squash/core/batch.py`: batch loop, output path resolution, progress/eta, cancellation
- `src/squash/gui/main_window.py`: main window, thread-safe UI queue, busy state, geometry fitting
- `src/squash/gui/dialogs.py`: shared dialogs, `center_on_parent`, `fit_to_content`
- `src/squash/config/manager.py`: `Settings` dataclass and persistence
