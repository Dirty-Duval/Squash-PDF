# Squash Development Setup Guide

Quick guide to get started with Squash PDF Compressor development.

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/downloads)
- **Ghostscript** - [Download](https://www.ghostscript.com/releases/gsdnld.html) (for testing)
- **Windows 10/11** (64-bit)

## Quick Start (5 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/ACWul/Squash.git
cd Squash
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

**Activate**:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes testing tools)
pip install -r requirements-dev.txt
```

### 4. Run Application

```bash
python -m squash.main
```

Or:

```bash
cd src
python -m squash.main
```

## Development Workflow

### Project Structure

```
Squash/
├── src/
│   ├── squash/           # Main application code
│   │   ├── core/         # Compression engine
│   │   ├── gui/          # GUI components
│   │   ├── config/       # Configuration
│   │   ├── utils/        # Utilities
│   │   └── main.py       # Entry point
│   └── tests/            # Test suite
│       ├── unit/         # Unit tests
│       └── integration/  # Integration tests
├── docs/                 # Documentation
├── installer/            # Installer files
└── .github/              # CI/CD workflows
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=squash

# Run specific test file
pytest src/tests/unit/test_presets.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code (auto-fix)
black src/squash

# Check formatting
black --check src/squash

# Lint code
flake8 src/squash

# Type checking
mypy src/squash
```

### Making Changes

1. **Create branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** and test:
   ```bash
   pytest
   black src/squash
   flake8 src/squash
   ```

3. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Common Tasks

### Add New Preset

Edit `src/squash/core/presets.py`:

```python
"custom": Preset(
    name="custom",
    display_name="Custom Name",
    description="Description",
    dpi=200,
    color_image_resolution=200,
    gray_image_resolution=200,
    mono_image_resolution=400,
    pdf_settings="/ebook",
    target_reduction="50%",
)
```

### Modify GUI

Edit `src/squash/gui/main_window.py` to change the interface.

### Change Default Settings

Edit `src/squash/config/manager.py` - `Settings` dataclass.

### Add New Test

Create file in `src/tests/unit/test_yourmodule.py`:

```python
import pytest

def test_something():
    # Your test code
    assert True
```

## Building for Distribution

### Create Executable (PyInstaller)

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --name Squash --windowed --onefile src/squash/main.py

# Output: dist/Squash.exe
```

### Create Installer (Inno Setup)

1. Install [Inno Setup](https://jrsoftware.org/isdl.php)
2. Download Ghostscript and place in `installer/ghostscript/`
3. Compile `installer/installer.iss`
4. Output: `installer/output/SquashSetup.exe`

## Troubleshooting

### "Module not found" Error

**Solution**: Ensure virtual environment is activated and dependencies installed.

```bash
pip install -r requirements-dev.txt
```

### Ghostscript Not Found

**For Development**:
- Install Ghostscript system-wide
- Add to PATH environment variable

**For Distribution**:
- Bundle Ghostscript in `installer/ghostscript/` folder

### Tests Failing

1. Check Python version (3.11+)
2. Update dependencies: `pip install -r requirements-dev.txt --upgrade`
3. Clear cache: `pytest --cache-clear`

### GUI Not Starting

1. Check CustomTkinter installed: `pip install customtkinter`
2. Check Python Tkinter: `python -m tkinter` (should open window)
3. Review logs in `%APPDATA%\Squash\logs\`

## Configuration Files

### pyproject.toml
Project metadata, dependencies, tool configurations

### requirements.txt
Production dependencies (runtime)

### requirements-dev.txt
Development dependencies (testing, linting)

### .gitignore
Files excluded from version control

### .github/workflows/build.yml
CI/CD pipeline configuration

## Environment Variables

None required for basic development. Optional:

- `APPDATA` - Application data directory (Windows default)
- `SQUASH_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR)

## IDE Setup

### VS Code (Recommended)

1. Install Python extension
2. Open workspace: `Squash.code-workspace` (create if needed)
3. Select interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → `venv`

**Recommended Extensions**:
- Python (Microsoft)
- Pylance
- Black Formatter
- Test Explorer UI

### PyCharm

1. Open project folder
2. Configure interpreter: Settings → Project → Python Interpreter → Add → Existing Environment → `venv`
3. Enable pytest: Settings → Tools → Python Integrated Tools → Testing → pytest

## Resources

- **Python Docs**: https://docs.python.org/3/
- **CustomTkinter Docs**: https://customtkinter.tomschimansky.com/
- **Ghostscript Docs**: https://www.ghostscript.com/doc/
- **PyInstaller Manual**: https://pyinstaller.org/en/stable/
- **Pytest Docs**: https://docs.pytest.org/

## Getting Help

- 📖 Read [CONTRIBUTING.md](CONTRIBUTING.md)
- 💬 Open [GitHub Discussions](https://github.com/ACWul/Squash/discussions)
- 🐛 Report [Issues](https://github.com/ACWul/Squash/issues)

---

**Happy Coding!** 🚀
