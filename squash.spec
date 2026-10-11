# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Squash PDF Compressor
Creates a standalone Windows executable with all dependencies bundled.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the base directory
block_cipher = None
base_dir = os.path.abspath(os.getcwd())

# Collect CustomTkinter data files (themes, assets)
customtkinter_datas = collect_data_files('customtkinter')

# Collect tkinterdnd2 data files (DLLs)
tkinterdnd2_datas = collect_data_files('tkinterdnd2')

# Add bundled Ghostscript (if available)
ghostscript_path = os.path.join(base_dir, 'ghostscript')
ghostscript_datas = []
if os.path.exists(ghostscript_path):
    ghostscript_datas = [(ghostscript_path, 'ghostscript')]
    print(f"Including bundled Ghostscript from: {ghostscript_path}")

# Add README and LICENSE files
readme_files = []
if os.path.exists(os.path.join(base_dir, 'README_DIST.txt')):
    readme_files.append((os.path.join(base_dir, 'README_DIST.txt'), '.'))
if os.path.exists(os.path.join(base_dir, 'LICENSE')):
    readme_files.append((os.path.join(base_dir, 'LICENSE'), '.'))

# Add brand assets (icon + theme used at runtime)
assets_datas = []
for asset_file in ['squash.ico', 'squash_theme.json']:
    asset_path = os.path.join(base_dir, 'assets', asset_file)
    if os.path.exists(asset_path):
        assets_datas.append((asset_path, 'assets'))

# Hidden imports needed for dependencies
hidden_imports = [
    'PIL._tkinter_finder',
    'PIL._imaging',
    'customtkinter',
    'tkinterdnd2',
]

a = Analysis(
    ['src\\squash\\__main__.py'],
    pathex=[base_dir, os.path.join(base_dir, 'src')],
    binaries=[],
    datas=customtkinter_datas + tkinterdnd2_datas + ghostscript_datas + readme_files + assets_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'black',
        'flake8',
        'mypy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Squash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Hide console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/squash.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Squash',
)
