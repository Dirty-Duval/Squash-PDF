"""
Auto-update support for Squash PDF Compressor.

Checks GitHub Releases for a newer version, downloads the installer to a
temp file, and launches it — Inno Setup handles removing the old installation.

Usage:
    checker = UpdateChecker()
    checker.check_async(callback=my_func)   # non-blocking
    # my_func(release: Optional[ReleaseInfo], network_error: bool)
    #   release is set when a newer version exists
    #   network_error is True when the check failed due to connectivity
"""

import json
import logging
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib import error as url_error
from urllib import request

logger = logging.getLogger(__name__)

APP_VERSION = "2.1.0"
GITHUB_REPO = "Dirty-Duval/Squash-PDF"
_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_REQUEST_TIMEOUT = 8  # seconds


def _parse_version(tag: str) -> tuple:
    """Parse a version string like 'v2.1.0' or '2.1.0' into a comparable tuple."""
    tag = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0,)


def _is_newer(remote_tag: str, local_version: str = APP_VERSION) -> bool:
    """Return True if remote_tag represents a version newer than local_version."""
    return _parse_version(remote_tag) > _parse_version(local_version)


@dataclass
class ReleaseInfo:
    """Metadata for an available GitHub release."""

    tag: str           # e.g. "v2.1.0"
    version: str       # tag without leading 'v'
    name: str          # release title
    body: str          # release notes (markdown)
    download_url: str  # URL of the Setup exe asset
    asset_name: str    # filename of the asset


class UpdateChecker:
    """Non-blocking GitHub release checker and one-click downloader."""

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def check_async(
        self,
        callback: Callable[[Optional[ReleaseInfo], bool], None],
    ) -> None:
        """Check for updates in a background daemon thread.

        Args:
            callback: Called with (release, network_error).
                      release is a ReleaseInfo when a newer version exists,
                      None when already up-to-date or on error.
                      network_error is True when the check failed due to a
                      connectivity or API problem (distinct from "up-to-date").
        """
        t = threading.Thread(target=self._check_worker, args=(callback,), daemon=True)
        t.start()

    def download(
        self,
        release: ReleaseInfo,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[Path]:
        """Download the release installer to a temp file.

        Args:
            release: ReleaseInfo returned by the update check.
            progress_callback: Optional callable(bytes_downloaded, total_bytes).
                               Called periodically during download.

        Returns:
            Path to the downloaded installer, or None on failure.
        """
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".exe",
                prefix="SquashSetup_",
                delete=False,
            )
            tmp_path = Path(tmp.name)
            tmp.close()

            req = request.Request(
                release.download_url,
                headers={"User-Agent": f"Squash/{APP_VERSION}"},
            )

            with request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk = 65536

                with open(tmp_path, "wb") as f:
                    while True:
                        data = resp.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        downloaded += len(data)
                        if progress_callback and total:
                            progress_callback(downloaded, total)

            logger.info(f"Downloaded installer to {tmp_path}")
            return tmp_path

        except Exception as exc:
            logger.error(f"Installer download failed: {exc}")
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            return None

    def install_and_quit(self, installer_path: Path, quit_callback: Callable) -> None:
        """Launch the installer then quit the app.

        The Inno Setup installer's /CLOSEAPPLICATIONS flag handles removing
        the running exe before overwriting it.

        Args:
            installer_path: Path to the downloaded Setup exe.
            quit_callback: Called (on the main thread via self.after) to
                           destroy the application window.
        """
        try:
            subprocess.Popen(
                [
                    str(installer_path),
                    "/SILENT",
                    "/CLOSEAPPLICATIONS",
                    "/RESTARTAPPLICATIONS",
                ],
                creationflags=subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            logger.info("Installer launched, quitting app")
        except Exception as exc:
            logger.error(f"Failed to launch installer: {exc}")
            raise
        finally:
            quit_callback()

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _check_worker(self, callback: Callable[[Optional[ReleaseInfo], bool], None]) -> None:
        """Background thread: fetch latest release and call callback."""
        try:
            release = self._fetch_latest()
            if release and _is_newer(release.tag):
                logger.info(f"Update available: {release.tag}")
                callback(release, False)
            else:
                logger.debug("No update available")
                callback(None, False)
        except Exception as exc:
            logger.warning(f"Update check failed: {exc}")
            callback(None, True)

    def _fetch_latest(self) -> Optional[ReleaseInfo]:
        """Fetch and parse the latest GitHub release."""
        req = request.Request(
            _API_URL,
            headers={"User-Agent": f"Squash/{APP_VERSION}"},
        )

        with request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())

        tag = data.get("tag_name", "")
        if not tag:
            return None

        # Find the Setup exe asset
        download_url = ""
        asset_name = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".exe") and "setup" in name.lower():
                download_url = asset.get("browser_download_url", "")
                asset_name = name
                break

        if not download_url:
            logger.warning("Latest release has no Setup .exe asset")
            return None

        return ReleaseInfo(
            tag=tag,
            version=tag.lstrip("v").strip(),
            name=data.get("name", tag),
            body=data.get("body", "").strip(),
            download_url=download_url,
            asset_name=asset_name,
        )
