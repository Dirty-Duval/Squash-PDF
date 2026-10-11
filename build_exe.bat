@echo off
REM Build script for Squash PDF Compressor executable
REM Uses PyInstaller to create standalone Windows executable

echo ============================================================
echo Building Squash PDF Compressor Executable
echo ============================================================
echo.

REM Clean previous builds
echo [1/4] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist\Squash rmdir /s /q dist\Squash
echo       Done.
echo.

REM Run PyInstaller
echo [2/4] Running PyInstaller...
set "PY=python"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"
%PY% -m PyInstaller squash.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)
echo       Done.
echo.

REM Check if executable was created
echo [3/4] Verifying executable...
if not exist dist\Squash\Squash.exe (
    echo.
    echo ERROR: Squash.exe was not created!
    pause
    exit /b 1
)
echo       Executable created successfully.
echo.

REM Display results
echo [4/4] Build complete!
echo.
echo ============================================================
echo Executable location: dist\Squash\Squash.exe
echo ============================================================
echo.
echo You can now test the executable by running:
echo   dist\Squash\Squash.exe
echo.
echo To create an installer, run: build_installer.bat
echo.
pause
