@echo off
REM Build script for Squash PDF Compressor Windows Installer
REM Requires Inno Setup 6.2+ installed from https://jrsoftware.org/isinfo.php

echo ============================================================
echo Building Squash PDF Compressor Installer
echo ============================================================
echo.

REM Check if Inno Setup is installed
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" set "INNO_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo ERROR: Inno Setup not found!
    echo.
    echo Please install Inno Setup 6.2+ from:
    echo https://jrsoftware.org/isinfo.php
    echo.
    echo Looked in: C:\Program Files (x86)\Inno Setup 6 and %%LOCALAPPDATA%%\Programs\Inno Setup 6
    echo.
    pause
    exit /b 1
)

REM Check if executable exists
if not exist "dist\Squash\Squash.exe" (
    echo ERROR: Squash.exe not found!
    echo.
    echo Please build the executable first by running:
    echo   build_exe.bat
    echo.
    pause
    exit /b 1
)

REM Create installer output directory
if not exist "dist\installer" mkdir "dist\installer"

REM Read the application version from the single source of truth
for /f "usebackq delims=" %%v in (`python -c "import sys; sys.path.insert(0, 'src'); import squash; print(squash.__version__)"`) do set "APP_VERSION=%%v"
if "%APP_VERSION%"=="" (
    echo ERROR: Could not read version from src\squash\__init__.py
    pause
    exit /b 1
)
echo Building installer for version %APP_VERSION%

REM Build installer
echo [1/2] Running Inno Setup compiler...
"%INNO_PATH%" /DAppVersion=%APP_VERSION% squash.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup compilation failed!
    pause
    exit /b 1
)
echo       Done.
echo.

REM Display results
echo [2/2] Build complete!
echo.
echo ============================================================
echo Installer created successfully!
echo ============================================================
echo.
for %%F in (dist\installer\SquashSetup-*.exe) do (
    echo Location: %%F
    echo Size:
    dir "%%F" | find "SquashSetup"
)
echo.
echo You can now:
echo 1. Test the installer on this machine
echo 2. Copy to a clean Windows VM for testing
echo 3. Upload to GitHub Releases
echo.
pause
