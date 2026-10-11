@echo off
REM Complete build pipeline for Squash PDF Compressor
REM Builds executable and installer in one command

echo ============================================================
echo Squash PDF Compressor - Complete Build Pipeline
echo ============================================================
echo.
echo This will:
echo 1. Build the PyInstaller executable
echo 2. Create the Inno Setup installer
echo.
pause

REM Step 1: Build executable
echo.
echo ============================================================
echo STEP 1: Building Executable
echo ============================================================
call build_exe.bat
if errorlevel 1 (
    echo.
    echo ERROR: Executable build failed!
    pause
    exit /b 1
)

REM Step 2: Build installer
echo.
echo ============================================================
echo STEP 2: Building Installer
echo ============================================================
call build_installer.bat
if errorlevel 1 (
    echo.
    echo ERROR: Installer build failed!
    pause
    exit /b 1
)

REM Success
echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Both the executable and installer have been created:
echo.
echo Executable: dist\Squash\Squash.exe
echo Installer:  dist\installer\SquashSetup-^<version^>.exe
echo.
echo Next steps:
echo 1. Test the installer on this machine or a clean VM
echo 2. Create a GitHub Release tagged with the version (e.g. v2.2.0)
echo 3. Upload the SquashSetup-^<version^>.exe installer to the release
echo.
pause
