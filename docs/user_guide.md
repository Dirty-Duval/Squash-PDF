# Squash PDF Compressor - User Guide

**Version 2.0** | Simple PDF compression for Windows

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Features](#features)
5. [Quality Presets](#quality-presets)
6. [Managing Custom Presets](#managing-custom-presets)
7. [Settings](#settings)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

Squash is a simple, user-friendly PDF compression tool designed for non-technical users. It helps you reduce PDF file sizes quickly and easily without uploading your files to the cloud.

### Key Features

- ✅ **100% Local Processing** - No internet required, complete privacy
- ✅ **Simple Interface** - Just drag, drop, and compress
- ✅ **3 Quality Presets** - Small, Medium, High Quality
- ✅ **Batch Processing** - Compress multiple PDFs at once
- ✅ **Fast** - Process files at 5+ MB/s
- ✅ **Free & Open Source** - AGPL-3.0 licensed

---

## Installation

### System Requirements

- **Operating System**: Windows 10 (64-bit) or Windows 11
- **Disk Space**: ~100 MB free space
- **RAM**: 4 GB minimum, 8 GB recommended
- **Permissions**: Administrator rights for installation

### Installation Steps

1. **Download** the installer from [GitHub Releases](https://github.com/ACWul/Squash/releases)
2. **Run** `SquashSetup.exe`
3. **Follow** the installation wizard
4. **Launch** from desktop shortcut or Start Menu

### Uninstallation

- **Windows Settings** → Apps → Squash PDF Compressor → Uninstall
- Or use the uninstaller in the installation folder

---

## Quick Start

### Compress Your First PDF (30 seconds)

1. **Launch Squash** from your desktop or Start Menu
2. **Add files**:
   - **Drag & drop** PDF files directly into the drop zone, OR
   - **Click** the "📁 Drag & Drop PDFs Here" area to browse files
3. **Select quality**: Choose Small, Medium, or High Quality
4. **Click** "🗜️ COMPRESS NOW"
5. **Done!** Compressed files are saved in the same folder with `_compressed` suffix

### Example

**Before**: `invoice.pdf` (2.4 MB)
**After**: `invoice_compressed.pdf` (0.6 MB) - 75% smaller!

---

## Features

### File Selection

**Add Files - Two Easy Ways**

1. **Drag & Drop** (Fastest!)
   - Drag PDF files from Windows Explorer
   - Drop them onto the "📁 Drag & Drop PDFs Here" area
   - Multiple files supported - drag as many as you need
   - Invalid files (non-PDFs) will be automatically filtered out

2. **Browse Files**
   - Click the drop zone to open file browser
   - Select one or multiple PDF files (Ctrl+Click for multiple)
   - Click Open to add them to the list

**Remove Files**
- Click the ✕ button next to any file to remove it from the list

**File Information**
- File name and size are displayed for each selected file
- Total size shown at the top of the list

**Visual Feedback**
- The drop zone highlights when you drag files over it
- Shows "📥 Release to Add Files" when ready to drop
- Invalid files trigger an error message with details

### Quality Presets

Choose the right preset for your use case:

| Preset | DPI | Best For | Size Reduction |
|--------|-----|----------|----------------|
| **Small** | 72 | Email, web viewing | 70-90% |
| **Medium** | 150 | General documents, reading | 50-70% |
| **High Quality** | 300 | Printing, archival | 30-50% |

### Compression Process

1. **Progress Bar** shows overall completion percentage
2. **Status Text** shows current file being processed
3. **Result Dialog** shows:
   - Number of files compressed
   - Total size reduction (MB and %)
   - Duration
   - Any errors

---

## Quality Presets

### Small (72 DPI)

**Best for**: Web viewing, email attachments, screen reading

**Characteristics**:
- Smallest file size
- Lower image quality
- Fast compression
- 70-90% size reduction

**Use when**:
- Sending via email (file size limits)
- Uploading to websites
- Long-term archival not needed

### Medium (150 DPI) - DEFAULT

**Best for**: General documents, everyday use

**Characteristics**:
- Balanced quality and size
- Good readability on screen
- Moderate compression speed
- 50-70% size reduction

**Use when**:
- General document sharing
- Internal office documents
- Digital reading

### High Quality (300 DPI)

**Best for**: Printing, professional documents

**Characteristics**:
- Best image quality
- Larger file size
- Slower compression
- 30-50% size reduction

**Use when**:
- Documents will be printed
- Professional presentations
- High-quality archival

---

## Managing Custom Presets

Starting with version 2.0, Squash allows you to create, edit, and manage custom compression presets tailored to your specific needs. This gives you full control over compression parameters while maintaining the simplicity of preset-based compression.

### Opening the Preset Editor

To access the custom preset manager:

1. Click the **"⚙️ Manage Presets"** button in the main window (located to the right of the quality preset options)
2. The Custom Preset Editor dialog will open

The editor features a two-pane interface:
- **Left pane**: List of all available presets (built-in and custom)
- **Right pane**: Editor form for viewing and modifying preset parameters

### Creating a New Custom Preset

To create a new custom preset:

1. Click the **"+ New"** button in the preset list pane
2. A new preset template will be created with default values
3. Fill in the required fields in the editor pane:
   - **Preset Name**: Unique identifier (1-50 characters, alphanumeric, spaces, hyphens, underscores)
   - **Display Name**: User-friendly name shown in the main window (1-100 characters)
   - **Description**: Purpose and use case for the preset
4. Configure compression parameters:
   - **Quality Level**: Choose PDF settings preset (/screen, /ebook, /printer, /prepress)
   - **Color Image Resolution**: DPI for color images (50-2400)
   - **Grayscale Image Resolution**: DPI for grayscale images (50-2400)
   - **Monochrome Image Resolution**: DPI for black & white images (50-2400)
   - **Target Reduction**: Expected file size reduction percentage
5. Click **"💾 Save"** to save the new preset

**Tip**: Start with one of the example presets (see [docs/examples/](../examples/README.md)) and modify it to suit your needs.

### Editing Existing Custom Presets

To modify a custom preset:

1. Select the preset from the list (custom presets are marked with a star ⭐)
2. Make your changes in the editor pane
3. Click **"💾 Save"** to save changes

**Note**: Built-in presets (Small, Medium, High Quality) cannot be edited. They are protected to ensure consistent behavior. Create a custom preset based on these if you need modifications.

### Deleting Custom Presets

To remove a custom preset:

1. Select the preset from the list
2. Click the **"🗑️ Delete"** button
3. Confirm deletion in the dialog

**Note**: Built-in presets cannot be deleted. Only custom presets you've created can be removed.

### Importing Presets

You can import presets from JSON files:

1. Click the **"↓ Import"** button
2. Select a preset JSON file
3. If a preset with the same name already exists:
   - Choose **"Overwrite"** to replace the existing preset
   - Choose **"Rename"** to import with a different name
   - Enter a new name when prompted
4. The imported preset will appear in your preset list

**Where to find presets**:
- Example presets in [docs/examples/](../examples/)
- Presets shared by other users
- Presets you've exported from another installation

### Exporting Presets

To share or backup a custom preset:

1. Select the preset from the list
2. Click the **"↑ Export"** button
3. Choose a location and filename
4. The preset will be saved as a JSON file

**Use cases**:
- Share presets with colleagues
- Backup before reinstalling
- Transfer presets between computers
- Contribute presets to the community

### Understanding Compression Parameters

**PDF Settings** (`pdf_settings`):
- **/screen** (72 DPI): Maximum compression for screen viewing
- **/ebook** (150 DPI): Balanced compression for digital reading
- **/printer** (300 DPI): High quality for printing
- **/prepress** (300+ DPI): Maximum quality for professional printing

**Image Resolution Parameters**:
- **Color Image Resolution**: Controls quality of color images and photos
- **Grayscale Image Resolution**: Controls quality of grayscale images
- **Monochrome Image Resolution**: Controls quality of black & white images (text, line art)

**DPI Guidelines**:
- **50-96 DPI**: Web viewing, email, maximum compression
- **120-150 DPI**: General documents, digital reading
- **200-300 DPI**: Printing, presentations
- **600-2400 DPI**: Professional printing, archival (monochrome only)

**Target Reduction**: Expected file size reduction as a percentage range (e.g., "60-75%"). This is informational only and helps document the preset's purpose.

### Best Practices

**Naming Conventions**:
- Use descriptive names that indicate purpose (e.g., "email_friendly", "print_quality")
- Include target use case in description
- Use consistent naming if creating multiple related presets

**Parameter Selection**:
- Match resolution to output medium (screen vs. print)
- Higher DPI = larger files but better quality
- Monochrome resolution can be higher than color/grayscale without large file size impact
- Test presets with representative documents before bulk processing

**Organization**:
- Create presets for common workflows (email, internal docs, client delivery, archival)
- Export important presets for backup
- Delete unused presets to keep list manageable
- Document special-purpose presets in descriptions

**Quality vs. Size Trade-offs**:
- Start with a built-in preset and adjust incrementally
- Test compressed output before committing to large batches
- Keep one "safe" preset (higher quality) for important documents
- Consider your audience's needs (screen readers need less than printers)

### Preset Storage

Custom presets are stored in:
```
%APPDATA%\Squash\presets\custom_presets.json
```

This file is automatically created when you save your first custom preset. You can manually edit this file if needed, but it's recommended to use the preset editor interface to avoid validation errors.

---

## Settings

### General Settings

**Default Quality Preset**
- Choose which preset is selected by default

**Output Location**
- Same folder as original (default)
- Custom folder (choose specific directory)

**Theme**
- System (follows Windows theme)
- Light mode
- Dark mode

### Advanced Settings

**Compression Timeout**
- Maximum time per file (default: 300 seconds)
- Increase for very large files

**Log Level**
- Controls amount of logging
- Options: Error, Warning, Info, Debug

### Privacy Settings

**Check for Updates**
- Automatically check for new versions (requires internet)
- Default: Enabled

**Store History**
- Keep history of compressed files
- Default: Enabled

---

## Troubleshooting

### Common Issues

**"File Not Found" Error**

**Cause**: File was moved or deleted after selection

**Solution**: Remove from list and re-add the file

---

**"Invalid PDF" Error**

**Cause**: File is corrupted or not a valid PDF

**Solution**:
- Try opening in Adobe Reader to verify
- If corrupted, obtain a clean copy
- Convert from another format if needed

---

**"Compression Failed" Error**

**Cause**: File uses unsupported PDF features

**Solution**:
- Try a different quality preset
- Check if PDF is password-protected
- Verify sufficient disk space

---

**"Ghostscript Not Found" Error**

**Cause**: Ghostscript not properly installed

**Solution**:
- Reinstall Squash
- If using portable version, ensure Ghostscript is bundled

---

### Getting Help

**Before contacting support**:
1. Check this User Guide
2. Search [GitHub Issues](https://github.com/ACWul/Squash/issues)
3. Review [FAQ](#faq) below

**To report a bug**:
1. Go to [GitHub Issues](https://github.com/ACWul/Squash/issues)
2. Click "New Issue"
3. Provide:
   - Windows version
   - Squash version
   - Steps to reproduce
   - Error messages
   - Screenshots (if applicable)

---

## FAQ

### General Questions

**Q: Is Squash really free?**

A: Yes! Squash is 100% free and open-source (AGPL-3.0 license).

**Q: Does Squash upload my files to the cloud?**

A: No! All processing is 100% local. Your files never leave your computer.

**Q: Can I use Squash for commercial purposes?**

A: Yes, Squash can be used for personal and commercial purposes.

**Q: What file formats are supported?**

A: Only PDF files. Other formats (images, Word docs) are not supported.

---

### Technical Questions

**Q: How does compression work?**

A: Squash uses Ghostscript to reduce image resolution, remove metadata, and optimize PDF structure without losing text quality.

**Q: Will compression reduce text quality?**

A: No! Text remains crisp and readable. Only images are compressed.

**Q: Can I compress password-protected PDFs?**

A: Not currently. Remove the password first, then compress.

**Q: Can I undo compression?**

A: The original file is never modified. Simply delete the compressed version if not satisfied.

**Q: How fast is compression?**

A: Approximately 5 MB/s on standard hardware (varies by preset and file complexity).

---

### Usage Questions

**Q: What's the maximum file size?**

A: Up to 2 GB per file (Ghostscript limitation).

**Q: How many files can I compress at once?**

A: No limit! Process hundreds of files in one batch.

**Q: Where are compressed files saved?**

A: By default, in the same folder as the original with `_compressed` suffix.

**Q: Can I compress the same file multiple times?**

A: Yes, but diminishing returns after the first compression.

**Q: Which preset should I use?**

A: For most cases, use **Medium** (default). Use **Small** for email, **High** for printing.

---

## Tips & Best Practices

### Maximizing Compression

1. **Start with Medium preset** - Good balance for most cases
2. **Use Small for emails** - When file size limits apply
3. **Compress scanned PDFs first** - They compress the most
4. **Don't compress twice** - Diminishing returns

### Organizing Files

1. **Use batch processing** - Select all files at once
2. **Keep originals** - Don't delete originals until verified
3. **Rename outputs** - Consider more descriptive names
4. **Test compressed PDFs** - Open and verify before sharing

### Performance Tips

1. **Close other applications** - Free up RAM
2. **Process large batches overnight** - For hundreds of files
3. **Use High preset sparingly** - Slower compression
4. **Store files on SSD** - Faster read/write speeds

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file dialog |
| F1 | Show help/about |
| Esc | Cancel compression |

---

## Version History

**v2.0.0** (Current)
- Ground-up rebuild with modern architecture
- Improved GUI with CustomTkinter
- 3 simple quality presets
- Batch processing support
- Better error handling

**v1.0.0** (Legacy)
- Initial release
- Basic compression functionality

---

## Credits

**Squash PDF Compressor** is powered by:
- [Ghostscript](https://www.ghostscript.com/) - PDF processing engine
- [CustomTkinter](https://customtkinter.tomschimansky.com/) - Modern GUI framework
- [Python](https://www.python.org/) - Programming language

---

## License

Squash is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

This means:
- ✅ Free to use, modify, and distribute
- ✅ Open source code available
- ✅ Commercial use allowed
- ⚠️ Modifications must be shared under same license
- ⚠️ Network use = distribution (AGPL requirement)

Full license: [LICENSE](../LICENSE)

---

## Contact & Support

- 🌐 **Website**: [github.com/ACWul/Squash](https://github.com/ACWul/Squash)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/ACWul/Squash/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/ACWul/Squash/discussions)
- 📧 **Email**: [your.email@example.com]

---

**Thank you for using Squash!** 🎉

*Last Updated: 2025-12-10 | Version 2.0.0*
