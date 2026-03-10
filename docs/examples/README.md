# Example Custom Presets

This directory contains example custom preset JSON files that can be imported into Squash PDF Compressor.

## How to Use

1. Download the desired preset JSON file
2. Open Squash PDF Compressor
3. Click "⚙️ Manage Presets" button
4. Click "↓ Import" button
5. Select the downloaded JSON file
6. The preset will be added to your preset list

## Available Presets

### 🌐 Web Optimized (`preset_web_optimized.json`)
- **DPI**: 96
- **Target Reduction**: 75-85%
- **Best For**: Websites, online documents, screen viewing
- **Description**: Maximum compression while maintaining readability on screens

### 🖨️ Print Quality (`preset_print_quality.json`)
- **DPI**: 300
- **Target Reduction**: 20-35%
- **Best For**: Professional printing, presentations, archival
- **Description**: Minimal compression with high quality for printed materials

### 📧 Email Friendly (`preset_email_friendly.json`)
- **DPI**: 120
- **Target Reduction**: 60-75%
- **Best For**: Email attachments, file sharing, mobile viewing
- **Description**: Balanced compression targeting files under 2MB

## Creating Your Own Presets

You can create custom presets by:

1. **Using the Preset Editor**:
   - Click "⚙️ Manage Presets"
   - Click "+ New"
   - Configure settings
   - Click "Save"

2. **Manually Creating JSON**:
   ```json
   {
     "version": "2.0.0",
     "preset": {
       "name": "my_custom",
       "display_name": "My Custom Preset",
       "description": "Description of what this preset does",
       "dpi": 150,
       "color_image_resolution": 150,
       "gray_image_resolution": 150,
       "mono_image_resolution": 600,
       "pdf_settings": "/ebook",
       "target_reduction": "50-70%",
       "is_custom": true
     }
   }
   ```

## Parameter Reference

### DPI Ranges
- **Minimum**: 50 DPI
- **Maximum**: 2400 DPI
- **Recommended**:
  - Web: 72-96 DPI
  - Email: 120-150 DPI
  - Print: 300 DPI
  - Professional Print: 600-1200 DPI

### PDF Settings
- `/screen`: Lowest quality, smallest files (72 DPI)
- `/ebook`: Medium quality (150 DPI)
- `/printer`: High quality for printing (300 DPI)
- `/prepress`: Professional printing quality (300 DPI+)
- `/default`: Ghostscript default settings

## Sharing Presets

To share your custom presets with others:

1. Select the preset in the Preset Editor
2. Click "↑ Export"
3. Save the JSON file
4. Share the file with others

Recipients can import the preset using the "↓ Import" button.

## License

These example presets are provided as-is under the AGPL-3.0 license.
