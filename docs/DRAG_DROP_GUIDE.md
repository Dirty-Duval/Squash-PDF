# Drag-and-Drop Feature Guide

**Squash PDF Compressor v2.0+** | Feature Documentation

---

## Overview

The drag-and-drop feature allows users to add PDF files to Squash by simply dragging them from Windows Explorer and dropping them onto the application window. This provides a faster, more intuitive alternative to the traditional file browser.

### Key Features

- ✅ **Multi-file support** - Drag and drop multiple PDFs at once
- ✅ **Visual feedback** - Drop zone highlights when files are dragged over
- ✅ **Automatic validation** - Only PDF files are accepted
- ✅ **Error handling** - Clear messages for invalid files
- ✅ **Graceful fallback** - Works without drag-drop library (browse mode)

---

## User Guide

### How to Use Drag-and-Drop

1. **Open Squash** application
2. **Open Windows Explorer** and navigate to your PDF files
3. **Select one or more PDFs** (Ctrl+Click for multiple selection)
4. **Drag the files** over the Squash window
5. **Watch for visual feedback** - The drop zone will highlight with "📥 Release to Add Files"
6. **Release the mouse button** to drop the files
7. **Files are added** to the compression queue instantly!

### Visual States

| State | Display | Description |
|-------|---------|-------------|
| **Ready** | 📁 Drag & Drop PDFs Here<br>or click to Browse Files | Default state, ready to receive files |
| **Drag Over** | 📥 Release to Add Files | Files are being dragged over the drop zone |
| **Drop Success** | Files added to list | Valid PDFs are added to the queue |
| **Drop Error** | Error dialog with details | Invalid files trigger an error message |

### File Validation

When you drop files, Squash automatically validates them:

✅ **Accepted:**
- Files with `.pdf` extension
- Files that exist and are accessible
- Regular files (not directories)

❌ **Rejected:**
- Non-PDF files (`.docx`, `.jpg`, `.txt`, etc.)
- Missing or inaccessible files
- Directories/folders
- Files already in the list

### Error Messages

If you drop invalid files, you'll see an error dialog explaining what went wrong:

```
❌ Invalid Files

The following files were not added:

report.docx (not a PDF)
image.jpg (not a PDF)
missing.pdf (not found)

Only PDF files can be compressed.
```

**Note:** If you drop a mix of valid and invalid files, the valid PDFs will be added and an error will show for the invalid ones.

---

## Technical Documentation

### Architecture

The drag-and-drop feature is implemented using **tkinterdnd2**, a Python wrapper for the tkDnD Tk extension.

#### Components

1. **CTkDnD Class** - Custom CustomTkinter window with DnD support
2. **Drop Zone Widget** - The clickable label that receives drops
3. **Event Handlers** - Functions that process drag-and-drop events
4. **File Parser** - Parses Windows file paths with spaces
5. **Validator** - Checks file validity before adding

### Implementation Details

#### Custom CTk Class with DnD Support

```python
if DRAG_DROP_AVAILABLE:
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter window with drag-and-drop support."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    # Fallback to regular CTk if tkinterdnd2 not available
    CTkDnD = ctk.CTk
```

**Why this approach?**
- CustomTkinter's `CTk` class doesn't natively support tkinterdnd2
- Multiple inheritance combines `CTk` (modern GUI) with `DnDWrapper` (drag-drop)
- Graceful fallback ensures app works without drag-drop library

#### Event Registration

```python
def _setup_drag_drop(self):
    """Set up drag and drop functionality."""
    if not DRAG_DROP_AVAILABLE:
        return

    # Register drop zone
    self.drop_label.drop_target_register(DND_FILES)
    self.drop_label.dnd_bind('<<Drop>>', self._on_drop)
    self.drop_label.dnd_bind('<<DragEnter>>', self._on_drag_enter)
    self.drop_label.dnd_bind('<<DragLeave>>', self._on_drag_leave)
```

**Events:**
- `<<Drop>>` - Files are dropped on the widget
- `<<DragEnter>>` - Cursor enters the drop zone while dragging
- `<<DragLeave>>` - Cursor leaves the drop zone

#### File Path Parsing

Windows file paths with spaces are enclosed in braces `{}`:
- Single file: `C:\Users\Name\document.pdf`
- File with spaces: `{C:\Users\Name\My Documents\report.pdf}`
- Multiple files: `{C:\path one\file1.pdf} {C:\path two\file2.pdf} C:\simple.pdf`

**Parser Logic:**
```python
if files_str.startswith('{'):
    # Parse brace-enclosed paths
    files = []
    current = ""
    in_braces = False

    for char in files_str:
        if char == '{':
            in_braces = True
            current = ""
        elif char == '}':
            in_braces = False
            if current:
                files.append(current.strip())
            current = ""
        elif in_braces:
            current += char
        elif char == ' ' and not in_braces:
            if current:
                files.append(current.strip())
            current = ""
        else:
            current += char
else:
    # Simple space-separated paths
    files = files_str.split()
```

#### File Validation

Each dropped file goes through validation:

```python
for file_str in files:
    file_path = Path(file_str)

    # Check 1: Does file exist?
    if not file_path.exists():
        invalid_files.append(f"{file_path.name} (not found)")
        continue

    # Check 2: Is it a file (not directory)?
    if not file_path.is_file():
        invalid_files.append(f"{file_path.name} (not a file)")
        continue

    # Check 3: Is it a PDF?
    if file_path.suffix.lower() != '.pdf':
        invalid_files.append(f"{file_path.name} (not a PDF)")
        continue

    # Check 4: Is it already in the list?
    if file_path not in self.selected_files:
        valid_files.append(file_path)
```

#### Visual Feedback

**Drag Enter (Highlight):**
```python
def _on_drag_enter(self, event):
    self.drop_label.configure(
        text="📥 Release to Add Files",
        fg_color=("gray75", "gray25")  # Light/dark mode colors
    )
    return event.action
```

**Drag Leave (Reset):**
```python
def _on_drag_leave(self, event):
    self.drop_label.configure(
        text="📁 Drag & Drop PDFs Here\n\nor click to Browse Files",
        fg_color="transparent"
    )
```

---

## Dependencies

### Required

- **tkinterdnd2** >= 0.4.0
  - Install: `pip install tkinterdnd2>=0.4.0`
  - Purpose: Native drag-and-drop support for Windows, macOS, and Linux
  - License: BSD-3-Clause

### Optional Fallback

If tkinterdnd2 is not installed:
- Drag-and-drop is disabled
- Browse button still works normally
- User sees log message: "Drag-and-drop not available - install tkinterdnd2"

---

## Platform Compatibility

### Windows ✅ Fully Supported
- Windows 10 (64-bit)
- Windows 11
- File paths with spaces handled correctly
- Multiple file drops supported

### macOS ⚠️ Should Work
- macOS 10.14+ (untested)
- tkinterdnd2 supports macOS
- File path format may differ

### Linux ⚠️ Should Work
- Most distributions with Tk 8.6+
- tkinterdnd2 supports Linux
- File path format may differ

---

## Troubleshooting

### Drag-and-Drop Not Working

**Symptom:** Files don't drop, no visual feedback

**Possible Causes:**
1. **tkinterdnd2 not installed**
   - Check log: `Drag-and-drop not available - install tkinterdnd2`
   - Solution: `pip install tkinterdnd2>=0.4.0`

2. **Permission issues**
   - Running app as admin while dragging from non-admin Explorer
   - Solution: Run both with same permissions

3. **Antivirus interference**
   - Some antivirus tools block drag-drop
   - Solution: Add Squash to antivirus exceptions

### Files Not Accepted

**Symptom:** Files drop but aren't added

**Possible Causes:**
1. **Not PDF files**
   - Check file extension (must be `.pdf`)
   - Solution: Convert files to PDF first

2. **Files already in list**
   - Duplicate prevention active
   - Solution: Remove from list first, then re-add

3. **Permission issues**
   - Files are read-protected
   - Solution: Check file permissions

### Visual Feedback Missing

**Symptom:** Drop zone doesn't highlight

**Possible Causes:**
1. **Theme issues**
   - Some CustomTkinter themes may not show highlighting clearly
   - Solution: Try different theme in settings

2. **Event binding failed**
   - Check log for errors during initialization
   - Solution: Restart application

---

## Development Guide

### Adding Drag-and-Drop to New Widgets

To add drag-and-drop to other widgets in Squash:

```python
# 1. Register widget as drop target
widget.drop_target_register(DND_FILES)

# 2. Bind drop event
widget.dnd_bind('<<Drop>>', your_drop_handler)

# 3. Optional: Add visual feedback
widget.dnd_bind('<<DragEnter>>', your_enter_handler)
widget.dnd_bind('<<DragLeave>>', your_leave_handler)

# 4. Implement handler
def your_drop_handler(event):
    files_str = event.data
    # Parse and process files
    return event.action
```

### Testing Drag-and-Drop

**Manual Testing:**
1. Create test PDFs with various characteristics:
   - Normal names: `test.pdf`
   - Spaces in name: `test file.pdf`
   - Special chars: `test_file (copy).pdf`
   - Long paths: `C:\Very\Long\Path\With\Many\Folders\file.pdf`

2. Test scenarios:
   - Single file drop
   - Multiple file drop (2, 5, 10, 20 files)
   - Mix of PDF and non-PDF files
   - Dragging from different locations (Desktop, Documents, Network drives)
   - Drag without releasing (should highlight, then reset)

**Automated Testing:**
Currently, tkinterdnd2 doesn't support automated testing well. Manual testing recommended.

### Performance Considerations

**File Count Limits:**
- No hard limit on dropped files
- GUI responsiveness may degrade with 50+ files
- Consider async processing for very large batches

**Memory Usage:**
- File paths stored as `Path` objects (minimal memory)
- No file content loaded during drag-drop
- Validation is lightweight (stat calls only)

---

## Future Enhancements

Potential improvements for drag-and-drop:

### Planned (Phase 3)
- [ ] Folder drop support (automatically find all PDFs in folder)
- [ ] Drag-and-drop ordering (rearrange files in queue)
- [ ] Drop zone animation (smooth highlight transition)

### Considered (Phase 4)
- [ ] Preview on hover (show first page of PDF)
- [ ] Smart duplicate detection (same content, different name)
- [ ] Undo last drop action
- [ ] Drag files out to export

---

## References

### External Documentation
- [tkinterdnd2 GitHub](https://github.com/pmgagne/tkinterdnd2) - Library source
- [tkinterdnd2 PyPI](https://pypi.org/project/tkinterdnd2/) - Package info
- [CustomTkinter Docs](https://customtkinter.tomschimansky.com/) - GUI framework
- [CustomTkinter DnD Discussion](https://github.com/TomSchimansky/CustomTkinter/discussions/470) - Integration guide

### Internal Documentation
- [User Guide](user_guide.md) - End-user instructions
- [API Reference](API_REFERENCE.md) - Code documentation
- [CONTINUE_HERE.md](../CONTINUE_HERE.md) - Development status

---

## Changelog

### v2.0.0 (2025-12-10) - Initial Release
- ✅ Implemented drag-and-drop with tkinterdnd2
- ✅ Custom CTkDnD class for CustomTkinter integration
- ✅ Visual feedback on drag enter/leave
- ✅ Windows path parsing with brace handling
- ✅ File validation (PDF-only, existence, type)
- ✅ Error dialogs for invalid files
- ✅ Graceful fallback when library unavailable
- ✅ Multi-file drop support
- ✅ Duplicate prevention

---

## License

This feature is part of Squash PDF Compressor, licensed under AGPL-3.0.

The tkinterdnd2 library is licensed under BSD-3-Clause.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-10
**Author:** Claude Sonnet 4.5 + ACWul
**Status:** Complete ✅
