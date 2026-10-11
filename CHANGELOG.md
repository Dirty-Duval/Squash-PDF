# Changelog

All notable changes to Squash PDF Compressor.

## 2.2.1 - 2026-10-11

### Fixed
- The application started invisibly in 2.2.0: the main window called `withdraw()` while building itself, and CustomTkinter 6 then never reveals the root window on Windows. The process ran with no window to click. Every 2.2.0 user should take this update.
- The silent-upgrade path no longer drops the desktop shortcut.

## 2.2.0 - 2026-10-10

### Fixed
- The **Default Output Folder** setting is now honoured. Previously every file was written next to its original regardless of the setting.
- The **file name pattern**, **time limit** and **log level** settings are now applied (they were stored but ignored).
- The saved **theme** is applied at startup instead of only after opening Settings.
- Window size, maximised state and the last-used preset are remembered between runs.
- Ghostscript no longer auto-rotates pages (`-dAutoRotatePages=/None`). The `/screen` and `/ebook` profiles silently rotated landscape pages based on text direction.
- The **High Quality** preset keeps original colours (CMYK stays CMYK) instead of converting everything to RGB.
- Progress highlighting matched the wrong file when files were added in non-alphabetical order.
- Files could be removed from the list, or new files dropped, while a batch was running.
- A failed or cancelled Ghostscript run no longer leaves a half-written output file: output is written to a `.part` file and moved into place only on success.
- Password-protected PDFs were reported as success with a broken output (Ghostscript exits 0 for them). They are now reported clearly.
- Per-file results were missing from the Compression Results view when the output was larger than the input (the chart refused to draw).
- Update checker could crash with an unbound variable if the temp file could not be created.
- A `%` in an output file name no longer confuses Ghostscript.
- Files with very long names failed with "Unable to open the initial device" because the temporary output path exceeded Windows' 260-character limit; the temporary file now has a short name.
- Settings and history files are written atomically and as UTF-8.
- History timestamps are stored as ISO text (the implicit SQLite datetime adapter is deprecated in Python 3.12+).
- The unit tests no longer read and write the developer's real custom presets in `%APPDATA%`.

### Added
- **Already-optimised handling**: when Ghostscript's output would be larger than the original (common for JBIG2 scans and optimised web PDFs; 13 of 55 real files in testing), the larger file is discarded, the original is kept and the result says by how much it would have grown. A Settings option keeps the larger output if you really want it.
- **Cancel** button during compression (stops after the current page; partial output is discarded).
- **Real per-file progress** from Ghostscript page markers, byte-weighted overall progress, speed and ETA.
- **Plain-language errors** for damaged files, password-protected PDFs, permission and disk errors, instead of raw Ghostscript stack traces.
- **Add Folder**, **Clear All**, output-location hint and preset description on the main window.
- **Open Output Folder** button in the results view.
- **Duplicate** in the preset editor so built-in presets can be used as a starting point; **colour handling** option per preset (keep original / RGB / grayscale); no more pop-ups after every save.
- Settings: file name pattern with live preview, per-file time limit, Open Log Folder, history on/off, Reset to Defaults; the dialog offers to create a missing output folder.
- Failed compressions are recorded in history so the success rate is meaningful; history keeps 500 entries instead of 50.
- Windows and dialogs open sized to their content so nothing is hidden or needs scrolling.
- Single source of truth for the version (`squash.__version__`), used by the app, settings, updater and installer build.
- Test-suite: Ghostscript wrapper, batch processor and filesystem unit tests plus integration tests that run the bundled Ghostscript (skipped when it is absent). 148 tests.

### Changed
- `BatchProcessor.process_batch` takes `output_dir`, `naming_pattern`, `timeout`, `cancel_event` and `result_callback`; the progress callback receives a `BatchProgress` object. Files are processed in the order given.
- `GhostscriptWrapper.compress` raises `GhostscriptError` instead of returning a bool and reports progress through a callback.
- `CompressionEngine.compress` adds error codes `E006` (cancelled), `E007` (timeout) and `E008` (output would overwrite input).
- Shared, themed dialogs (`squash.gui.dialogs`) replace the per-window copies and the native `messagebox` pop-ups.
- Default log level is INFO; logs rotate at 5 MB.
- Output PDFs are written as PDF 1.5 instead of 1.4 (object streams save a few percent; supported by every reader since Acrobat 6).
- `pytest` works without `pytest-cov` (coverage is opt-in) and finds the package via `pythonpath`.

## 2.1.0 - 2026-03-10
- Auto-update via GitHub Releases, brand theme and icon, installer close-app handling.

## 2.0.0 - 2026-01-08
- Rebuild on CustomTkinter with presets, batch processing, history, custom presets and charts.
