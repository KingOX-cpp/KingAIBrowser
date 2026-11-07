"""Download official platform installers and optionally open their native UI."""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from _kingai_stdio import failure, child_environment

BASE = "https://161.118.255.111/download/"
MAX_BYTES = 3 * 1024 * 1024 * 1024


class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise failure("INSTALL_REDIRECT_REJECTED", "Installer redirects must use HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def target():
    machine = platform.machine().lower()
    if sys.platform == "win32":
        native = os.environ.get("PROCESSOR_ARCHITEW6432", os.environ.get("PROCESSOR_ARCHITECTURE", machine)).lower()
        if native not in ("amd64", "x86_64"):
            raise failure("INSTALL_UNSUPPORTED_PLATFORM", "Windows installers require Intel/AMD x64; ARM and 32-bit Windows are unsupported")
        return "windows-x64", "KingAIBrowserSetup.exe"
    if sys.platform == "darwin":
        if machine not in ("arm64", "aarch64"):
            # Apple Silicon can run an x86_64 Python under Rosetta.
            probe = subprocess.run(["/usr/sbin/sysctl", "-in", "hw.optional.arm64"], capture_output=True, text=True)
            if probe.returncode != 0 or probe.stdout.strip() != "1":
                raise failure("INSTALL_UNSUPPORTED_PLATFORM", "The macOS installer supports Apple Silicon only")
        return "macos-arm64", "KingAIBrowser.dmg"
    raise failure("INSTALL_UNSUPPORTED_PLATFORM", "Installers support Windows x64 and Apple Silicon macOS only")


def install(*, download_dir=None, download_only=False, sha256=None, reuse_existing=True):
    """Download an installer and optionally open its UI; never claim UI completion.

    download_dir controls download storage, not the browser installation folder.
    Existing compatible MCP discovery can be reused unless explicitly disabled.
    """
    system, filename = target()
    if sha256 is not None and (len(sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha256)):
        raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
    if reuse_existing and not download_only:
        from _kingai_discovery import discover_mcp
        try:
            return {"status": "existing_installation", "mcpExecutable": discover_mcp(), "platform": system}
        except Exception as error:
            if getattr(error, "code", None) not in ("MCP_NOT_FOUND", "MCP_NOT_INSTALLED"):
                raise
    directory = Path(download_dir or (r"D:\code\KingAIBrowser-downloads" if sys.platform == "win32" else Path.home() / "Downloads/KingAIBrowser")).expanduser()
    if not directory.is_absolute():
        raise ValueError("download_dir must be absolute")
    directory.mkdir(parents=True, exist_ok=True)
    # Keep partial files separate; do not overwrite a previous installer.
    work = Path(tempfile.mkdtemp(prefix="download-", dir=directory))
    partial = work / (filename + ".part")
    destination = work / filename
    digest = hashlib.sha256()
    total = 0
    started = time.monotonic()
    try:
        with build_opener(SecureRedirect()).open(BASE + filename, timeout=30) as response, partial.open("xb") as output:
            if response.status != 200 or "text/html" in response.headers.get("Content-Type", "").lower():
                raise failure("INSTALL_DOWNLOAD_FAILED", "The server did not return an installer file")
            declared = response.headers.get("Content-Length")
            while True:
                if time.monotonic() - started > 600:
                    raise failure("INSTALL_DOWNLOAD_TIMEOUT", "Installer download exceeded ten minutes")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise failure("INSTALL_DOWNLOAD_TOO_LARGE", "Installer exceeds the 3 GiB download limit")
                output.write(chunk)
                digest.update(chunk)
            if total == 0 or (declared is not None and total != int(declared)):
                raise failure("INSTALL_DOWNLOAD_INCOMPLETE", "Installer size did not match the response")
        actual = digest.hexdigest()
        if sha256 is not None and actual != sha256.lower():
            raise failure("INSTALL_HASH_MISMATCH", "Installer SHA-256 did not match the supplied trusted checksum")
        if system == "windows-x64":
            with partial.open("rb") as file:
                if file.read(2) != b"MZ":
                    raise failure("INSTALL_FORMAT_INVALID", "Downloaded Windows file is not an executable")
        partial.rename(destination)
    except URLError as error:
        raise failure("INSTALL_DOWNLOAD_FAILED", "HTTPS download failed; verify network access and certificate validity. TLS verification is never disabled", reason=str(error.reason)) from error
    finally:
        if partial.exists():
            partial.unlink()
    result = {"status": "downloaded", "platform": system, "installerPath": str(destination), "sha256": actual,
              "checksumVerified": sha256 is not None, "bytes": total, "url": BASE + filename}
    if not download_only:
        command = [str(destination)] if sys.platform == "win32" else ["/usr/bin/open", str(destination)]
        environment = child_environment(language=None, file_roots=None, download_dir=None, artifact_dir=None)
        try:
            subprocess.Popen(command, env=environment, close_fds=True)
        except OSError as error:
            raise failure("INSTALL_LAUNCH_FAILED", "Installer was downloaded but could not be opened", installerPath=str(destination), reason=str(error)) from error
        result["status"] = "installer_started"
        result["nextStep"] = "Complete the Windows installer or macOS DMG installation, open Manager and sign in, then run doctor. Installation and MCP availability have not been verified."
    return result
