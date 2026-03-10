# Squash API Reference

Complete API documentation for Squash PDF Compressor v2.0

---

## Table of Contents

1. [Core Modules](#core-modules)
2. [Configuration](#configuration)
3. [GUI Components](#gui-components)
4. [Utilities](#utilities)
5. [Data Models](#data-models)
6. [Error Codes](#error-codes)

---

## Core Modules

### squash.core.compression

Main compression engine for PDF processing.

#### CompressionEngine

**Class**: `CompressionEngine(ghostscript_path: Optional[Path] = None)`

Main PDF compression engine using Ghostscript.

**Parameters**:
- `ghostscript_path` (Path, optional): Custom Ghostscript executable path. If None, auto-detects.

**Methods**:

##### compress()

```python
def compress(
    self,
    input_path: Path,
    output_path: Optional[Path] = None,
    preset: str = "medium",
    timeout: int = 300,
) -> CompressionResult
```

Compress a PDF file.

**Parameters**:
- `input_path` (Path): Path to input PDF file
- `output_path` (Path, optional): Path for output file. If None, generates `{filename}_compressed.pdf`
- `preset` (str): Quality preset name (`"small"`, `"medium"`, `"high"`)
- `timeout` (int): Maximum compression time in seconds (default: 300)

**Returns**: `CompressionResult` with operation details

**Raises**:
- `FileNotFoundError`: If input file doesn't exist
- `ValueError`: If preset is invalid
- `RuntimeError`: If Ghostscript fails

**Example**:
```python
from pathlib import Path
from squash.core.compression import CompressionEngine

engine = CompressionEngine()
result = engine.compress(
    input_path=Path("document.pdf"),
    preset="medium"
)

if result.success:
    print(f"Compressed: {result.format_sizes()}")
    print(f"Reduction: {result.reduction_percent:.1f}%")
else:
    print(f"Error: {result.error_message}")
```

##### validate_pdf()

```python
def validate_pdf(self, path: Path) -> bool
```

Check if file is a valid PDF.

**Parameters**:
- `path` (Path): Path to file

**Returns**: `True` if valid PDF, `False` otherwise

**Example**:
```python
if engine.validate_pdf(Path("document.pdf")):
    print("Valid PDF")
```

#### CompressionResult

**Dataclass**: `CompressionResult`

Result of a PDF compression operation.

**Attributes**:
- `success` (bool): Whether compression succeeded
- `input_path` (str): Input file path
- `output_path` (str | None): Output file path
- `original_size` (int): Original file size in bytes
- `compressed_size` (int | None): Compressed file size in bytes
- `reduction_percent` (float | None): Size reduction percentage
- `duration` (float): Processing time in seconds
- `preset_used` (str): Quality preset used
- `timestamp` (datetime): Operation timestamp
- `error_code` (str | None): Error code if failed
- `error_message` (str | None): Error message if failed

**Methods**:

```python
def get_size_reduction_mb(self) -> Optional[float]
```
Returns size reduction in megabytes.

```python
def format_sizes(self) -> str
```
Returns formatted size string (e.g., "2.4 MB → 0.6 MB").

---

### squash.core.presets

Quality preset management.

#### PresetManager

**Class**: `PresetManager()`

Manages compression quality presets, including built-in and custom user-created presets.

**Methods**:

##### get_preset()

```python
def get_preset(self, name: str) -> Preset
```

Get preset by name.

**Parameters**:
- `name` (str): Preset name (built-in: `"small"`, `"medium"`, `"high"` or custom preset name)

**Returns**: `Preset` object

**Raises**: `KeyError` if preset not found

**Example**:
```python
from squash.core.presets import PresetManager

manager = PresetManager()
preset = manager.get_preset("medium")
print(f"{preset.display_name}: {preset.description}")
```

##### list_presets()

```python
def list_presets(self) -> List[Preset]
```

Get list of all available presets (built-in and custom).

**Returns**: List of `Preset` objects sorted by name

##### get_preset_names()

```python
def get_preset_names(self) -> List[str]
```

Get list of all preset names.

**Returns**: List of preset name strings

##### get_default_preset()

```python
def get_default_preset(self) -> Preset
```

Get default preset (medium quality).

**Returns**: Default `Preset` object

##### add_custom_preset()

```python
def add_custom_preset(self, preset: Preset) -> bool
```

Add a new custom preset.

**Parameters**:
- `preset` (Preset): Preset object to add (must have `is_custom=True`)

**Returns**: `True` if successful

**Raises**:
- `ValueError`: If preset validation fails or name already exists
- `IOError`: If unable to save to file

**Example**:
```python
from squash.core.presets import PresetManager, Preset

manager = PresetManager()
custom_preset = Preset(
    name="email_friendly",
    display_name="Email Friendly",
    description="Balanced compression suitable for email attachments",
    dpi=120,
    color_image_resolution=120,
    gray_image_resolution=120,
    mono_image_resolution=400,
    pdf_settings="/ebook",
    target_reduction="60-75%",
    is_custom=True
)

manager.add_custom_preset(custom_preset)
```

##### update_preset()

```python
def update_preset(self, old_name: str, updated_preset: Preset) -> bool
```

Update an existing custom preset.

**Parameters**:
- `old_name` (str): Current preset name
- `updated_preset` (Preset): Updated preset object

**Returns**: `True` if successful

**Raises**:
- `ValueError`: If trying to modify built-in preset or validation fails
- `KeyError`: If old_name preset doesn't exist
- `IOError`: If unable to save to file

**Example**:
```python
# Get existing preset
preset = manager.get_preset("email_friendly")

# Modify parameters
preset.dpi = 150
preset.color_image_resolution = 150

# Update
manager.update_preset("email_friendly", preset)
```

##### delete_preset()

```python
def delete_preset(self, name: str) -> bool
```

Delete a custom preset.

**Parameters**:
- `name` (str): Preset name to delete

**Returns**: `True` if successful

**Raises**:
- `ValueError`: If trying to delete built-in preset
- `KeyError`: If preset doesn't exist
- `IOError`: If unable to save to file

**Example**:
```python
manager.delete_preset("email_friendly")
```

##### export_preset()

```python
def export_preset(self, name: str, export_path: Path) -> bool
```

Export a preset to JSON file.

**Parameters**:
- `name` (str): Preset name to export
- `export_path` (Path): Path where JSON file will be saved

**Returns**: `True` if successful

**Raises**:
- `KeyError`: If preset doesn't exist
- `IOError`: If unable to write file

**Example**:
```python
from pathlib import Path

manager.export_preset("email_friendly", Path("my_preset.json"))
```

##### import_preset()

```python
def import_preset(self, import_path: Path) -> Preset
```

Import a preset from JSON file.

**Parameters**:
- `import_path` (Path): Path to JSON preset file

**Returns**: Imported `Preset` object (not automatically added to manager)

**Raises**:
- `FileNotFoundError`: If import file doesn't exist
- `ValueError`: If JSON is invalid or preset validation fails
- `IOError`: If unable to read file

**Example**:
```python
from pathlib import Path

# Import preset object
preset = manager.import_preset(Path("my_preset.json"))

# Check if name conflicts, then add
if preset.name in manager.get_preset_names():
    # Handle conflict (rename or overwrite)
    preset.name = "imported_preset"

manager.add_custom_preset(preset)
```

**Note**: Custom presets are automatically persisted to `%APPDATA%\Squash\presets\custom_presets.json`.

#### Preset

**Dataclass**: `Preset`

Compression quality preset configuration.

**Attributes**:
- `name` (str): Internal preset name (1-50 characters, alphanumeric + spaces/hyphens/underscores)
- `display_name` (str): Display name for UI (1-100 characters)
- `description` (str): Preset description
- `dpi` (int): Target DPI (50-2400)
- `color_image_resolution` (int): Color image DPI (50-2400)
- `gray_image_resolution` (int): Grayscale image DPI (50-2400)
- `mono_image_resolution` (int): Monochrome image DPI (50-2400)
- `pdf_settings` (str): Ghostscript PDF settings (`"/screen"`, `"/ebook"`, `"/printer"`, `"/prepress"`)
- `target_reduction` (str): Expected size reduction range (e.g., "60-75%")
- `is_custom` (bool): Whether preset is custom (True) or built-in (False). Default: False

**Built-in Presets**:

| Name | DPI | Description | Target Reduction | is_custom |
|------|-----|-------------|------------------|-----------|
| small | 72 | Smallest file size for web viewing | 70-90% | False |
| medium | 150 | Balanced quality for general documents | 50-70% | False |
| high | 300 | High quality for printing | 30-50% | False |

**Validation Rules**:
- `name`: 1-50 characters, must match regex `^[a-zA-Z0-9_\-\s]+$`
- `display_name`: 1-100 characters
- `description`: Must not be empty
- DPI values: 50-2400 range
- `pdf_settings`: Must be one of `/screen`, `/ebook`, `/printer`, `/prepress`

**Methods**:

```python
def to_ghostscript_params(self) -> Dict[str, Any]
```

Convert preset to Ghostscript parameters dictionary.

**Example**:
```python
from squash.core.presets import Preset

# Create custom preset
preset = Preset(
    name="web_optimized",
    display_name="Web Optimized",
    description="Optimized for web viewing",
    dpi=96,
    color_image_resolution=96,
    gray_image_resolution=96,
    mono_image_resolution=300,
    pdf_settings="/screen",
    target_reduction="75-85%",
    is_custom=True
)

# Get Ghostscript parameters
params = preset.to_ghostscript_params()
```

---

### squash.core.batch

Batch processing for multiple PDFs.

#### BatchProcessor

**Class**: `BatchProcessor(engine: Optional[CompressionEngine] = None)`

Handles batch processing of multiple PDF files.

**Parameters**:
- `engine` (CompressionEngine, optional): Engine instance. If None, creates new one.

**Methods**:

##### process_batch()

```python
def process_batch(
    self,
    input_paths: List[Path],
    preset: str = "medium",
    recursive: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> BatchResult
```

Process multiple PDFs.

**Parameters**:
- `input_paths` (List[Path]): List of file/folder paths
- `preset` (str): Quality preset name
- `recursive` (bool): Process folders recursively
- `progress_callback` (Callable, optional): Callback function `(current, total, filename)`

**Returns**: `BatchResult` with operation details

**Example**:
```python
from pathlib import Path
from squash.core.batch import BatchProcessor

processor = BatchProcessor()

def progress(current, total, filename):
    print(f"[{current}/{total}] {filename}")

result = processor.process_batch(
    input_paths=[Path("folder/")],
    preset="small",
    recursive=True,
    progress_callback=progress
)

print(result.get_summary())
```

#### BatchResult

**Dataclass**: `BatchResult`

Result of batch PDF compression.

**Attributes**:
- `total_files` (int): Total files processed
- `successful` (int): Successfully compressed files
- `failed` (int): Failed compressions
- `total_size_before` (int): Total original size in bytes
- `total_size_after` (int): Total compressed size in bytes
- `total_reduction_percent` (float): Overall reduction percentage
- `duration` (float): Total processing time in seconds
- `file_results` (List[CompressionResult]): Individual file results

**Methods**:

```python
def get_summary(self) -> str
```

Returns human-readable summary string.

---

### squash.core.ghostscript

Ghostscript wrapper for PDF processing.

#### GhostscriptWrapper

**Class**: `GhostscriptWrapper(gs_path: Optional[Path] = None)`

Wrapper for Ghostscript PDF processing.

**Parameters**:
- `gs_path` (Path, optional): Custom Ghostscript executable path

**Attributes**:
- `gs_path` (Path): Path to Ghostscript executable

**Methods**:

##### compress()

```python
def compress(
    self,
    input_path: Path,
    output_path: Path,
    params: Dict[str, Any],
    timeout: int = 300,
) -> bool
```

Compress PDF using Ghostscript.

**Parameters**:
- `input_path` (Path): Input PDF path
- `output_path` (Path): Output PDF path
- `params` (Dict): Ghostscript parameters
- `timeout` (int): Maximum execution time in seconds

**Returns**: `True` if successful, `False` otherwise

**Raises**:
- `subprocess.TimeoutExpired`: If compression exceeds timeout
- `subprocess.CalledProcessError`: If Ghostscript fails

##### validate_pdf()

```python
def validate_pdf(self, path: Path) -> bool
```

Validate if file is a proper PDF (checks for PDF header).

##### get_version()

```python
def get_version(self) -> Optional[str]
```

Get Ghostscript version string.

---

## Configuration

### squash.config.manager

Configuration management for application settings.

#### ConfigManager

**Class**: `ConfigManager(config_dir: Optional[Path] = None)`

Manages application configuration and settings.

**Parameters**:
- `config_dir` (Path, optional): Custom config directory. If None, uses `%APPDATA%\Squash`

**Attributes**:
- `config_dir` (Path): Configuration directory path
- `config_file` (Path): Settings file path (`settings.json`)
- `settings` (Settings): Current settings object

**Methods**:

##### load_settings()

```python
def load_settings(self) -> Settings
```

Load settings from file. Returns default settings if file doesn't exist.

##### save_settings()

```python
def save_settings(self, settings: Optional[Settings] = None) -> bool
```

Save settings to file.

**Parameters**:
- `settings` (Settings, optional): Settings to save. If None, uses current settings.

**Returns**: `True` if successful, `False` otherwise

##### get()

```python
def get(self, key: str, default: Any = None) -> Any
```

Get setting value by key.

##### set()

```python
def set(self, key: str, value: Any) -> None
```

Set setting value.

##### reset_to_defaults()

```python
def reset_to_defaults(self) -> None
```

Reset all settings to defaults.

**Example**:
```python
from squash.config.manager import ConfigManager

config = ConfigManager()
config.load_settings()

# Get setting
theme = config.get("theme", "system")

# Update setting
config.set("default_preset", "high")
config.save_settings()
```

#### Settings

**Dataclass**: `Settings`

Application settings.

**Attributes**:

**General**:
- `version` (str): Settings version (default: "2.0.0")
- `default_preset` (str): Default quality preset (default: "medium")
- `output_location` (str): Output folder setting (default: "same_folder")
- `output_naming_pattern` (str): Output file naming (default: "{filename}_compressed.pdf")
- `theme` (str): UI theme (default: "system", options: "light", "dark", "system")

**Advanced**:
- `ghostscript_path` (str | None): Custom Ghostscript path (default: None)
- `compression_timeout` (int): Timeout in seconds (default: 300)
- `log_level` (str): Logging level (default: "WARNING")

**Privacy**:
- `check_updates` (bool): Auto-check for updates (default: True)
- `store_history` (bool): Store file history (default: True)

**Window State**:
- `window_width` (int): Window width in pixels (default: 700)
- `window_height` (int): Window height in pixels (default: 600)
- `window_maximized` (bool): Window maximized state (default: False)

**Methods**:

```python
def to_dict(self) -> dict
```

Convert settings to dictionary.

```python
@classmethod
def from_dict(cls, data: dict) -> "Settings"
```

Create settings from dictionary.

---

## GUI Components

### squash.gui.main_window

Main application window.

#### MainWindow

**Class**: `MainWindow()` (inherits from `customtkinter.CTk`)

Main GUI window for Squash PDF Compressor.

**Attributes**:
- `config_manager` (ConfigManager): Configuration manager
- `engine` (CompressionEngine): Compression engine
- `batch_processor` (BatchProcessor): Batch processor
- `selected_files` (List[Path]): Currently selected files

**Public Methods**:

##### add_files()

```python
def add_files(self) -> None
```

Open file dialog to add PDF files.

##### add_folder()

```python
def add_folder(self) -> None
```

Open folder dialog to add all PDFs in a folder.

##### remove_file()

```python
def remove_file(self, file_path: Path) -> None
```

Remove file from selected list.

##### start_compression()

```python
def start_compression(self) -> None
```

Start compression process (runs in background thread).

##### open_settings()

```python
def open_settings(self) -> None
```

Open settings dialog (placeholder in v2.0).

##### show_about()

```python
def show_about(self) -> None
```

Show about dialog.

**Dialog Methods**:

```python
def show_error(self, title: str, message: str) -> None
```

```python
def show_success(self, title: str, message: str) -> None
```

```python
def show_info(self, title: str, message: str) -> None
```

---

### squash.gui.results_dialog

Results dialog showing compression batch results with visual charts.

#### ResultsDialog

**Class**: `ResultsDialog(parent, batch_result: BatchResult)` (inherits from `customtkinter.CTkToplevel`)

Modal dialog displaying compression results with before/after comparison charts.

**Parameters**:
- `parent`: Parent window
- `batch_result` (BatchResult): Batch compression results

**Features**:
- Batch summary (total reduction, success/failure counts)
- Per-file comparison charts showing size reduction
- Scrollable interface for large batches
- Theme-aware visual design

**Example**:
```python
from squash.gui.results_dialog import ResultsDialog

# After batch compression
dialog = ResultsDialog(main_window, batch_result)
dialog.grab_set()  # Make modal
main_window.wait_window(dialog)
```

---

### squash.gui.components

Reusable UI components for charts and progress tracking.

#### ChartTheme

**Class**: `ChartTheme` (static methods)

Theme-aware color system for charts.

**Methods**:

##### get_colors()

```python
@staticmethod
def get_colors() -> Dict[str, str]
```

Get current theme colors for charts.

**Returns**: Dictionary with colors:
- `bg`: Background color
- `text`: Text color
- `primary`: Primary accent color
- `secondary`: Secondary accent color
- `success`: Success indicator color
- `error`: Error indicator color
- `grid`: Grid line color

**Example**:
```python
from squash.gui.components import ChartTheme

colors = ChartTheme.get_colors()
canvas.configure(bg=colors["bg"])
```

##### format_size()

```python
@staticmethod
def format_size(bytes: int) -> str
```

Format byte size to human-readable format (KB, MB, GB).

---

#### ComparisonBarChart

**Class**: `ComparisonBarChart(parent, width=400, height=120)` (inherits from `tk.Canvas`)

Horizontal bar chart comparing before/after file sizes.

**Parameters**:
- `parent`: Parent widget
- `width` (int): Canvas width
- `height` (int): Canvas height

**Methods**:

##### set_data()

```python
def set_data(
    self,
    original_size: int,
    compressed_size: int,
    filename: str = ""
) -> None
```

Set chart data and redraw.

**Parameters**:
- `original_size` (int): Original file size in bytes
- `compressed_size` (int): Compressed file size in bytes
- `filename` (str): Optional filename for display

**Example**:
```python
from squash.gui.components import ComparisonBarChart

chart = ComparisonBarChart(parent, width=600, height=150)
chart.pack(padx=10, pady=5)
chart.set_data(
    original_size=5242880,  # 5 MB
    compressed_size=1048576,  # 1 MB
    filename="document.pdf"
)
```

---

#### TrendLineChart

**Class**: `TrendLineChart(parent, width=600, height=300)` (inherits from `tk.Canvas`)

Line chart showing compression ratio trends over time.

**Parameters**:
- `parent`: Parent widget
- `width` (int): Canvas width
- `height` (int): Canvas height

**Methods**:

##### set_data()

```python
def set_data(self, data: List[Tuple[datetime, float]]) -> None
```

Set trend data and redraw chart.

**Parameters**:
- `data`: List of (timestamp, compression_ratio) tuples

**Example**:
```python
from squash.gui.components import TrendLineChart
from datetime import datetime

chart = TrendLineChart(parent, width=800, height=400)
chart.pack(padx=10, pady=10)

# Get trend data from history
trend_data = history_manager.get_trend_data(days=30)
chart.set_data(trend_data)
```

---

#### PresetComparisonBar

**Class**: `PresetComparisonBar(parent, width=600, height=300)` (inherits from `tk.Canvas`)

Grouped bar chart comparing preset effectiveness.

**Parameters**:
- `parent`: Parent widget
- `width` (int): Canvas width
- `height` (int): Canvas height

**Methods**:

##### set_data()

```python
def set_data(self, stats: Dict[str, Dict[str, float]]) -> None
```

Set preset statistics and redraw chart.

**Parameters**:
- `stats`: Dictionary of preset name to statistics:
  - `avg_ratio`: Average compression ratio
  - `count`: Number of uses
  - `total_saved`: Total bytes saved

**Example**:
```python
from squash.gui.components import PresetComparisonBar

chart = PresetComparisonBar(parent, width=700, height=350)
chart.pack(padx=10, pady=10)

# Get preset statistics from history
stats = history_manager.get_preset_statistics()
chart.set_data(stats)
```

---

#### EnhancedProgressTracker

**Class**: `EnhancedProgressTracker(parent)` (inherits from `customtkinter.CTkFrame`)

Enhanced progress widget with per-file status, speed, and ETA.

**Parameters**:
- `parent`: Parent widget

**Methods**:

##### update_progress()

```python
def update_progress(
    self,
    current_file: Path,
    file_progress: float,
    overall_progress: float,
    metrics: ProgressMetrics
) -> None
```

Update progress display.

**Parameters**:
- `current_file` (Path): Current file being processed
- `file_progress` (float): Per-file progress (0.0-1.0)
- `overall_progress` (float): Overall batch progress (0.0-1.0)
- `metrics` (ProgressMetrics): Speed and ETA metrics

##### reset()

```python
def reset(self) -> None
```

Reset progress tracker to initial state.

**Example**:
```python
from squash.gui.components import EnhancedProgressTracker, ProgressMetrics

tracker = EnhancedProgressTracker(parent)
tracker.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

# During compression
metrics = ProgressMetrics(
    speed_mbps=15.2,
    eta_seconds=45,
    bytes_processed=15728640
)
tracker.update_progress(
    current_file=Path("document.pdf"),
    file_progress=0.65,
    overall_progress=0.45,
    metrics=metrics
)

# After completion
tracker.reset()
```

---

#### ProgressMetrics

**Dataclass**: `ProgressMetrics`

Compression progress metrics.

**Attributes**:
- `speed_mbps` (float): Current compression speed in MB/s
- `eta_seconds` (float): Estimated time remaining in seconds
- `bytes_processed` (int): Total bytes processed so far

**Example**:
```python
from squash.gui.components import ProgressMetrics

metrics = ProgressMetrics(
    speed_mbps=12.5,
    eta_seconds=60,
    bytes_processed=10485760
)
print(f"Speed: {metrics.speed_mbps:.1f} MB/s")
print(f"ETA: {metrics.eta_seconds:.0f}s")
```

---

## Utilities

### squash.utils.logger

Logging configuration.

#### Functions

##### setup_logger()

```python
def setup_logger(
    name: str = "squash",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger
```

Set up application logger with console and optional file handler.

**Parameters**:
- `name` (str): Logger name
- `level` (int): Logging level
- `log_file` (Path, optional): Log file path

**Returns**: Configured `logging.Logger`

##### get_logger()

```python
def get_logger(name: str) -> logging.Logger
```

Get logger instance by name.

**Example**:
```python
from squash.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing file...")
```

---

### squash.utils.filesystem

Filesystem utilities.

#### FileSystemHelper

**Class**: `FileSystemHelper` (static methods)

Helper for filesystem operations.

**Methods**:

##### get_file_size_mb()

```python
@staticmethod
def get_file_size_mb(path: Path) -> float
```

Get file size in megabytes.

##### ensure_directory()

```python
@staticmethod
def ensure_directory(path: Path) -> None
```

Ensure directory exists, create if not.

##### get_unique_filename()

```python
@staticmethod
def get_unique_filename(path: Path) -> Path
```

Get unique filename if file already exists (adds _1, _2, etc).

##### copy_file()

```python
@staticmethod
def copy_file(src: Path, dst: Path, overwrite: bool = False) -> bool
```

Copy file safely.

##### delete_file()

```python
@staticmethod
def delete_file(path: Path) -> bool
```

Delete file safely.

##### get_app_data_dir()

```python
@staticmethod
def get_app_data_dir() -> Path
```

Get application data directory (`%APPDATA%\Squash` on Windows).

---

## Data Models

### File Paths

All file paths use `pathlib.Path` objects for cross-platform compatibility.

```python
from pathlib import Path

input_file = Path("C:/Documents/file.pdf")
output_file = Path("C:/Documents/file_compressed.pdf")
```

### Compression Results

See `CompressionResult` and `BatchResult` dataclasses above.

---

## Error Codes

### Compression Errors

| Code | Description | User Action |
|------|-------------|-------------|
| E001 | Input file not found | Check file path and try again |
| E002 | Invalid PDF file or corrupted | Verify PDF opens in reader |
| E003 | Invalid preset | Use "small", "medium", or "high" |
| E004 | Ghostscript compression failed | Try different preset or check file |
| E005 | Unexpected error | Check logs, report if persists |

### System Errors

| Error | Description | Solution |
|-------|-------------|----------|
| RuntimeError: "Ghostscript not found" | Ghostscript not installed | Install Ghostscript |
| FileNotFoundError | File doesn't exist | Verify path and file exists |
| PermissionError | Insufficient permissions | Run as admin or check file permissions |
| TimeoutError | Compression timeout | Increase timeout or check file size |

---

## Usage Examples

### Basic Compression

```python
from pathlib import Path
from squash.core.compression import CompressionEngine

# Initialize engine
engine = CompressionEngine()

# Compress single file
result = engine.compress(
    input_path=Path("document.pdf"),
    preset="medium"
)

if result.success:
    print(f"✓ Compressed: {result.format_sizes()}")
    print(f"  Reduction: {result.reduction_percent:.1f}%")
    print(f"  Duration: {result.duration:.1f}s")
else:
    print(f"✗ Failed: {result.error_message}")
```

### Batch Processing

```python
from pathlib import Path
from squash.core.batch import BatchProcessor

# Initialize processor
processor = BatchProcessor()

# Progress callback
def progress(current, total, filename):
    percent = (current / total) * 100
    print(f"[{percent:.0f}%] Processing: {filename}")

# Process folder
files = [Path("documents/")]
result = processor.process_batch(
    input_paths=files,
    preset="small",
    recursive=True,
    progress_callback=progress
)

# Print summary
print("\n" + result.get_summary())
```

### Custom Configuration

```python
from squash.config.manager import ConfigManager, Settings

# Load config
config = ConfigManager()
config.load_settings()

# Modify settings
config.settings.default_preset = "high"
config.settings.theme = "dark"
config.settings.compression_timeout = 600

# Save
config.save_settings()
```

### Preset Management

```python
from squash.core.presets import PresetManager

manager = PresetManager()

# List all presets
for preset in manager.list_presets():
    print(f"{preset.display_name} ({preset.dpi} DPI)")
    print(f"  {preset.description}")
    print(f"  Target: {preset.target_reduction}")
    print()

# Get specific preset
medium = manager.get_preset("medium")
params = medium.to_ghostscript_params()
print(f"Ghostscript params: {params}")
```

---

## Extension Points

### Custom Presets (Future)

Create custom presets by adding to `PresetManager.DEFAULT_PRESETS`:

```python
from squash.core.presets import Preset, PresetManager

custom = Preset(
    name="custom_web",
    display_name="Web Optimized",
    description="Optimized for web viewing",
    dpi=96,
    color_image_resolution=96,
    gray_image_resolution=96,
    mono_image_resolution=300,
    pdf_settings="/screen",
    target_reduction="80%",
)

manager = PresetManager()
manager.presets["custom_web"] = custom
```

### Custom GUI Widgets (Future)

Extend `MainWindow` to add custom functionality:

```python
from squash.gui.main_window import MainWindow

class CustomMainWindow(MainWindow):
    def __init__(self):
        super().__init__()
        self._add_custom_features()

    def _add_custom_features(self):
        # Add custom buttons, panels, etc.
        pass
```

---

## Version Compatibility

**Current Version**: 2.0.0

**Python**: 3.11+

**Dependencies**:
- customtkinter >= 5.2.0
- pillow >= 10.0.0

**External**:
- Ghostscript >= 9.50 (10.x recommended)

---

## Support

**Documentation**:
- User Guide: [user_guide.md](user_guide.md)
- Ghostscript Setup: [GHOSTSCRIPT_SETUP.md](GHOSTSCRIPT_SETUP.md)
- Setup Guide: [../SETUP.md](../SETUP.md)

**Issues**:
- Bug Reports: https://github.com/ACWul/Squash/issues
- Feature Requests: https://github.com/ACWul/Squash/issues

---

**Last Updated**: 2025-12-10
**Version**: 2.0.0
