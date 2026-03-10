"""
Ghostscript wrapper for PDF compression.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class GhostscriptWrapper:
    """Wrapper for Ghostscript PDF processing."""

    def __init__(self, gs_path: Optional[Path] = None):
        """
        Initialize Ghostscript wrapper.

        Args:
            gs_path: Custom Ghostscript executable path.
                    If None, searches system PATH and bundled version.
        """
        self.gs_path = gs_path or self._detect_ghostscript()
        if not self.gs_path:
            raise RuntimeError(
                "Ghostscript not found. Please install Ghostscript or reinstall the application."
            )

        logger.info(f"Using Ghostscript: {self.gs_path}")

    def _detect_ghostscript(self) -> Optional[Path]:
        """
        Detect Ghostscript installation.

        Priority:
        1. Bundled version (PyInstaller executable directory)
        2. System PATH

        Returns:
            Path to Ghostscript executable, or None if not found.
        """
        import sys

        # Check bundled version first (for packaged app)
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            exe_dir = Path(sys.executable).parent

            # Try _internal directory (PyInstaller default location)
            bundled_path = exe_dir / "_internal" / "ghostscript" / "bin" / "gswin64c.exe"
            if bundled_path.exists():
                logger.info(f"Using bundled Ghostscript: {bundled_path}")
                return bundled_path

            # Try direct subdirectory (alternative location)
            bundled_path = exe_dir / "ghostscript" / "bin" / "gswin64c.exe"
            if bundled_path.exists():
                logger.info(f"Using bundled Ghostscript: {bundled_path}")
                return bundled_path
        else:
            # Running from source - check relative path
            bundled_path = Path(__file__).parent.parent.parent.parent / "ghostscript" / "bin" / "gswin64c.exe"
            if bundled_path.exists():
                logger.info(f"Using bundled Ghostscript: {bundled_path}")
                return bundled_path

        # Check system PATH
        gs_names = ["gswin64c", "gswin32c", "gs"]
        for name in gs_names:
            gs_path = shutil.which(name)
            if gs_path:
                logger.info(f"Using system Ghostscript: {gs_path}")
                return Path(gs_path)

        return None

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        params: Dict[str, Any],
        timeout: int = 300,
    ) -> bool:
        """
        Compress PDF using Ghostscript.

        Args:
            input_path: Path to input PDF
            output_path: Path for output PDF
            params: Ghostscript parameters dictionary
            timeout: Maximum execution time in seconds

        Returns:
            True if successful, False otherwise

        Raises:
            subprocess.TimeoutExpired: If compression exceeds timeout
            subprocess.CalledProcessError: If Ghostscript fails
        """
        # Build Ghostscript command
        cmd = [
            str(self.gs_path),
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
        ]

        # Add custom parameters
        for key, value in params.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"-d{key}")
            else:
                cmd.append(f"-d{key}={value}")

        # Add input/output paths
        cmd.extend([f"-sOutputFile={output_path}", str(input_path)])

        logger.debug(f"Running Ghostscript: {' '.join(cmd)}")

        try:
            # Run Ghostscript (hide console window on Windows)
            import sys

            # Hide console window on Windows
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
                startupinfo=startupinfo,
            )

            # Verify output file was created
            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error(f"Output file not created or empty: {output_path}")
                return False

            logger.info(f"Successfully compressed: {input_path} -> {output_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Ghostscript timeout after {timeout}s for {input_path}")
            raise

        except subprocess.CalledProcessError as e:
            logger.error(f"Ghostscript failed: {e.stderr}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error during compression: {e}")
            return False

    def validate_pdf(self, path: Path) -> bool:
        """
        Validate if file is a proper PDF.

        Args:
            path: Path to file

        Returns:
            True if valid PDF, False otherwise
        """
        if not path.exists():
            return False

        try:
            # Check PDF header (simple validation)
            with open(path, "rb") as f:
                header = f.read(4)
                return header == b"%PDF"

        except Exception as e:
            logger.error(f"Error validating PDF {path}: {e}")
            return False

    def get_version(self) -> Optional[str]:
        """
        Get Ghostscript version.

        Returns:
            Version string, or None if unable to determine
        """
        try:
            result = subprocess.run(
                [str(self.gs_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Error getting Ghostscript version: {e}")
            return None
