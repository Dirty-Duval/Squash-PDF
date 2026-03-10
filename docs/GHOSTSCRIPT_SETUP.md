# Ghostscript Setup Guide for Squash

This guide covers Ghostscript installation and configuration for Squash PDF Compressor.

## What is Ghostscript?

Ghostscript is an open-source PDF and PostScript processor that powers Squash's compression engine. It's required for Squash to function.

**License**: AGPL-3.0 (same as Squash)
**Website**: https://www.ghostscript.com/

---

## Installation

### Windows (Standard Installation)

#### Option 1: Download and Install (Recommended for Users)

1. **Download Ghostscript**:
   - Visit: https://www.ghostscript.com/releases/gsdnld.html
   - Download the **Windows 64-bit** version
   - Example: `gs10.06.0-win64.exe` or newer

2. **Run Installer**:
   - Double-click the downloaded `.exe` file
   - Accept license agreement (AGPL-3.0)
   - Use default installation path: `C:\Program Files\gs\gs10.xx.x\`
   - Complete installation

3. **Verify Installation**:
   ```bash
   # Open Command Prompt or PowerShell
   gswin64c --version
   ```

   You should see output like:
   ```
   10.06.0
   ```

#### Option 2: Add to PATH (Optional)

If `gswin64c` command is not recognized:

1. **Find Ghostscript Path**:
   - Default: `C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe`

2. **Add to System PATH**:
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Under "System variables", find "Path"
   - Click "Edit" → "New"
   - Add: `C:\Program Files\gs\gs10.06.0\bin`
   - Click OK on all dialogs
   - Restart Command Prompt

3. **Test Again**:
   ```bash
   gswin64c --version
   ```

---

## Squash Integration

### Automatic Detection

Squash automatically detects Ghostscript in these locations (in order):

1. **Bundled version** (for packaged/portable app):
   - `installer/ghostscript/bin/gswin64c.exe`
   - Used in distributed `.exe` version

2. **System PATH**:
   - Searches for `gswin64c`, `gswin32c`, or `gs`
   - Works if you installed Ghostscript normally

3. **Custom path** (advanced):
   - Can be specified in settings (future feature)
   - For non-standard installations

### Verification

**Check Ghostscript Detection**:

```python
# Run this in Python to test detection
from pathlib import Path
from squash.core.ghostscript import GhostscriptWrapper

try:
    gs = GhostscriptWrapper()
    print(f"✓ Ghostscript found: {gs.gs_path}")
    print(f"✓ Version: {gs.get_version()}")
except RuntimeError as e:
    print(f"✗ Error: {e}")
```

**Expected Output**:
```
✓ Ghostscript found: C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe
✓ Version: 10.06.0
```

---

## Troubleshooting

### Issue: "Ghostscript not found"

**Symptoms**:
- Error when launching Squash
- Error message: "Ghostscript not found. Please install Ghostscript..."

**Solutions**:

1. **Verify Installation**:
   ```bash
   dir "C:\Program Files\gs"
   ```
   - Should show folder like `gs10.06.0`

2. **Check PATH**:
   ```bash
   where gswin64c
   ```
   - Should show path to `gswin64c.exe`
   - If not, add to PATH (see Option 2 above)

3. **Reinstall Ghostscript**:
   - Uninstall current version
   - Download latest from ghostscript.com
   - Install with default settings

4. **Check Permissions**:
   - Ensure `gswin64c.exe` is executable
   - Right-click → Properties → Security
   - Should have Read & Execute permissions

---

### Issue: Compression Fails with Ghostscript Errors

**Symptoms**:
- Ghostscript found but compression fails
- Error code E004 or E005

**Solutions**:

1. **Check PDF Validity**:
   - Open PDF in Adobe Reader
   - If corrupted, obtain clean copy

2. **Check Disk Space**:
   - Ensure sufficient free space (2x file size)
   - Temporary files created during compression

3. **Check File Permissions**:
   - Ensure read access to input PDF
   - Ensure write access to output folder

4. **Try Different Preset**:
   - Some PDFs compress better with different settings
   - Try "High Quality" preset if others fail

5. **Check Ghostscript Logs**:
   - View Squash logs: `%APPDATA%\Squash\logs\`
   - Look for Ghostscript error details

---

### Issue: Wrong Ghostscript Version Detected

**Symptoms**:
- Multiple Ghostscript installations
- Wrong version being used

**Solutions**:

1. **Uninstall Old Versions**:
   - Control Panel → Programs → Uninstall
   - Remove all Ghostscript versions except latest

2. **Clear PATH Duplicates**:
   - Check Environment Variables
   - Remove duplicate Ghostscript paths
   - Keep only latest version path

3. **Restart Applications**:
   - Close Squash completely
   - Restart Command Prompt/PowerShell
   - Launch Squash again

---

## For Developers

### Development Setup

When developing Squash, install Ghostscript system-wide:

```bash
# After installing Ghostscript
# Verify in Python
python -c "from squash.core.ghostscript import GhostscriptWrapper; print(GhostscriptWrapper().gs_path)"
```

### Testing Without Ghostscript

For unit tests that don't require actual compression:

```python
# tests/conftest.py has mock_ghostscript_path fixture
def test_something(mock_ghostscript_path):
    # Ghostscript calls are mocked
    engine = CompressionEngine()
    # Test non-compression logic
```

### Bundling for Distribution

For creating standalone `.exe` with PyInstaller:

1. **Download Ghostscript Binaries**:
   - Extract from installer or download portable version
   - Place in: `installer/ghostscript/bin/`
   - Include: `gswin64c.exe` and required `.dll` files

2. **PyInstaller Config**:
   ```python
   # squash.spec
   datas=[
       ('installer/ghostscript', 'ghostscript'),
   ]
   ```

3. **Detection Priority**:
   - Bundled version is checked first
   - Falls back to system installation

---

## Ghostscript Command-Line Usage

### Basic Compression Command

Squash uses commands like:

```bash
gswin64c ^
  -sDEVICE=pdfwrite ^
  -dCompatibilityLevel=1.4 ^
  -dNOPAUSE ^
  -dQUIET ^
  -dBATCH ^
  -dPDFSETTINGS=/ebook ^
  -dColorImageResolution=150 ^
  -sOutputFile=output.pdf ^
  input.pdf
```

### Manual Testing

Test Ghostscript manually:

```bash
# Navigate to folder with test PDF
cd "C:\Users\YourName\Documents"

# Compress with ebook preset
gswin64c -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dNOPAUSE -dQUIET -dBATCH -dPDFSETTINGS=/ebook -sOutputFile=test_compressed.pdf test.pdf
```

**Result**: Creates `test_compressed.pdf` in same folder

---

## Version Compatibility

### Tested Versions

Squash is tested with:
- ✅ Ghostscript 10.x (latest)
- ✅ Ghostscript 9.5x (stable)

### Minimum Requirements

- **Minimum**: Ghostscript 9.50+
- **Recommended**: Ghostscript 10.0+
- **Platform**: Windows 64-bit

### Checking Your Version

```bash
gswin64c --version
```

or

```bash
gswin64c -v
```

---

## Advanced Configuration

### Custom Ghostscript Path (Future Feature)

In future versions, you'll be able to specify custom path:

**Settings → Advanced → Ghostscript Path**

Useful for:
- Non-standard installations
- Multiple Ghostscript versions
- Portable installations
- Network drive installations

---

## Security Considerations

### Safe Usage

Ghostscript processes arbitrary PDF files, so:

1. **Keep Updated**:
   - Update Ghostscript regularly
   - Security patches released periodically

2. **Trusted PDFs**:
   - Only process PDFs from trusted sources
   - Malicious PDFs could exploit vulnerabilities

3. **Sandboxing**:
   - Squash runs Ghostscript in separate process
   - Limited file system access
   - Timeout protection (300s default)

4. **No Network Access**:
   - Ghostscript runs offline
   - No internet connection used
   - Complete privacy

---

## FAQ

**Q: Do I need to install Ghostscript separately?**

A: For the installer version, Ghostscript is bundled. For the Python version, yes, install separately.

**Q: Is Ghostscript free?**

A: Yes! Ghostscript is open-source (AGPL-3.0) and completely free.

**Q: Can I use a different PDF processor?**

A: Squash is designed specifically for Ghostscript. Other processors are not supported.

**Q: Why does Ghostscript use so much CPU?**

A: PDF compression is CPU-intensive. High-resolution images require significant processing.

**Q: Can I run multiple compressions simultaneously?**

A: Currently sequential (v2.0). Parallel processing planned for v2.1.

**Q: Does Ghostscript modify my original PDFs?**

A: No! Squash never modifies original files. Compressed files are always saved separately.

---

## Resources

**Official Ghostscript**:
- Website: https://www.ghostscript.com/
- Documentation: https://www.ghostscript.com/doc/
- Downloads: https://www.ghostscript.com/releases/gsdnld.html
- License: https://www.ghostscript.com/license.html

**Squash Documentation**:
- User Guide: [user_guide.md](user_guide.md)
- Setup Guide: [../SETUP.md](../SETUP.md)
- Troubleshooting: [user_guide.md#troubleshooting](user_guide.md#troubleshooting)

---

## Support

**Issues with Ghostscript Installation**:
- Check Ghostscript support: https://www.ghostscript.com/support.html
- Check Squash issues: https://github.com/ACWul/Squash/issues

**Issues with Squash Integration**:
- Report bug: https://github.com/ACWul/Squash/issues
- View logs: `%APPDATA%\Squash\logs\squash.log`

---

**Last Updated**: 2025-12-10
**Squash Version**: 2.0.0
**Tested with Ghostscript**: 10.06.0
