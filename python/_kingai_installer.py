"""Download official platform installers and optionally open their native UI."""
import hashlib
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from _kingai_stdio import failure, child_environment

BASE = "https://161.118.255.111/download/"
MAX_BYTES = 3 * 1024 * 1024 * 1024


class DownloadProgress:
    """Render periodic stderr updates even while a socket read is waiting."""
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.stream = sys.stderr
        self.started = time.monotonic()
        self.previous_time = self.started
        self.previous_bytes = 0
        self.downloaded = 0
        self.total = None
        self.phase = "Connecting"
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.thread = None
        self.width = 0

    @staticmethod
    def size(value):
        for unit in ("B", "KiB", "MiB", "GiB"):
            if value < 1024 or unit == "GiB":
                return f"{value:.1f} {unit}"
            value /= 1024

    def start(self):
        if self.enabled:
            self.render()
            self.thread = threading.Thread(target=self.run, name="kingai-download-progress", daemon=True)
            self.thread.start()

    def update(self, *, added=0, total=None, phase=None):
        with self.lock:
            self.downloaded += added
            if total is not None:
                self.total = total
            if phase is not None:
                self.phase = phase

    def render(self, final=False):
        if not self.enabled:
            return
        with self.lock:
            now = time.monotonic()
            speed = (self.downloaded / max(now - self.started, 0.001) if final else
                     (self.downloaded - self.previous_bytes) / max(now - self.previous_time, 0.001))
            self.previous_time, self.previous_bytes = now, self.downloaded
            elapsed = int(now - self.started)
            amount = self.size(self.downloaded)
            eta = "--"
            if self.total:
                amount += f" / {self.size(self.total)} ({min(100, self.downloaded / self.total * 100):.1f}%)"
                if speed > 0:
                    seconds = max(0, int((self.total - self.downloaded) / speed))
                    eta = f"{seconds // 60:02d}:{seconds % 60:02d}"
            else:
                amount += " / unknown total"
            line = f"{self.phase}: {amount} | {self.size(speed)}/s | elapsed {elapsed // 60:02d}:{elapsed % 60:02d} | ETA {eta}"
            terminal = self.stream.isatty()
            self.stream.write(("\r" if terminal else "") + line.ljust(self.width if terminal else 0) + ("\n" if final or not terminal else ""))
            self.stream.flush()
            self.width = len(line)

    def run(self):
        interval = 1 if self.stream.isatty() else 5
        while not self.finished.wait(interval):
            self.render()

    def stop(self, failed=False):
        self.finished.set()
        if self.thread:
            self.thread.join()
        if failed:
            self.update(phase="Download stopped")
        self.render(final=True)


def install_message(enabled, message):
    if enabled:
        print(message, file=sys.stderr, flush=True)


def default_download_dir():
    """Follow the system temporary directory, without choosing a drive or install path."""
    return Path(tempfile.gettempdir())


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


def install(*, download_dir=None, download_only=False, sha256=None, reuse_existing=True,
            progress=False, network_timeout=30):
    """Download an installer and optionally open its UI; never claim UI completion.

    download_dir controls download storage, not the browser installation folder.
    Existing compatible MCP discovery can be reused unless explicitly disabled.
    """
    system, filename = target()
    if not isinstance(progress, bool):
        raise ValueError("progress must be a boolean")
    if not isinstance(network_timeout, (int, float)) or isinstance(network_timeout, bool) or not math.isfinite(network_timeout) or network_timeout <= 0:
        raise ValueError("network_timeout must be a positive finite number of seconds")
    if sha256 is not None and (len(sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha256)):
        raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
    if reuse_existing and not download_only:
        from _kingai_discovery import discover_mcp
        try:
            executable = discover_mcp()
            install_message(progress, "Existing installation found; no download needed. Use --no-reuse-existing to download again.")
            return {"status": "existing_installation", "mcpExecutable": executable, "platform": system}
        except Exception as error:
            if getattr(error, "code", None) not in ("MCP_NOT_FOUND", "MCP_NOT_INSTALLED"):
                raise
    directory = (Path(download_dir) if download_dir is not None else default_download_dir()).expanduser()
    if not directory.is_absolute():
        raise ValueError("download_dir must be absolute")
    directory.mkdir(parents=True, exist_ok=True)
    # Keep partial files separate; do not overwrite a previous installer.
    work = Path(tempfile.mkdtemp(prefix="download-", dir=directory))
    partial = work / (filename + ".part")
    destination = work / filename
    digest = hashlib.sha256()
    total = 0
    install_message(progress, "Downloading " + filename + " to " + str(destination))
    reporter = DownloadProgress(progress)
    reporter.start()
    try:
        with build_opener(SecureRedirect()).open(BASE + filename, timeout=network_timeout) as response, partial.open("xb") as output:
            if response.status != 200 or "text/html" in response.headers.get("Content-Type", "").lower():
                raise failure("INSTALL_DOWNLOAD_FAILED", "The server did not return an installer file")
            declared = response.headers.get("Content-Length")
            expected_bytes = int(declared) if declared is not None else None
            if expected_bytes is not None and (expected_bytes <= 0 or expected_bytes > MAX_BYTES):
                raise failure("INSTALL_DOWNLOAD_SIZE_INVALID", "Declared installer size is invalid or exceeds 3 GiB")
            reporter.update(total=expected_bytes, phase="Downloading")
            read_chunk = getattr(response, "read1", response.read)
            while True:
                chunk = read_chunk(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise failure("INSTALL_DOWNLOAD_TOO_LARGE", "Installer exceeds the 3 GiB download limit")
                output.write(chunk)
                digest.update(chunk)
                reporter.update(added=len(chunk))
            if total == 0 or (expected_bytes is not None and total != expected_bytes):
                raise failure("INSTALL_DOWNLOAD_INCOMPLETE", "Installer size did not match the response")
        reporter.update(phase="Verifying file")
        actual = digest.hexdigest()
        if sha256 is not None and actual != sha256.lower():
            raise failure("INSTALL_HASH_MISMATCH", "Installer SHA-256 did not match the supplied trusted checksum")
        if system == "windows-x64":
            with partial.open("rb") as file:
                if file.read(2) != b"MZ":
                    raise failure("INSTALL_FORMAT_INVALID", "Downloaded Windows file is not an executable")
        partial.rename(destination)
        reporter.update(phase="Download complete")
    except TimeoutError as error:
        raise failure("INSTALL_NETWORK_TIMEOUT", "A network operation timed out; check the connection or increase --network-timeout", networkTimeout=network_timeout) from error
    except URLError as error:
        raise failure("INSTALL_DOWNLOAD_FAILED", "HTTPS download failed; verify network access and certificate validity. TLS verification is never disabled", reason=str(error.reason)) from error
    finally:
        reporter.stop(failed=sys.exc_info()[0] is not None)
        if partial.exists():
            partial.unlink()
    result = {"status": "downloaded", "platform": system, "installerPath": str(destination), "sha256": actual,
              "checksumVerified": sha256 is not None, "bytes": total, "url": BASE + filename}
    if not download_only:
        install_message(progress, "Opening installer UI. Complete installation in the system window.")
        command = [str(destination)] if sys.platform == "win32" else ["/usr/bin/open", str(destination)]
        environment = child_environment(language=None, file_roots=None, download_dir=None, artifact_dir=None)
        try:
            subprocess.Popen(command, env=environment, close_fds=True)
        except OSError as error:
            raise failure("INSTALL_LAUNCH_FAILED", "Installer was downloaded but could not be opened", installerPath=str(destination), reason=str(error)) from error
        result["status"] = "installer_started"
        result["nextStep"] = "Complete the Windows installer or macOS DMG installation, open Manager and sign in, then run doctor. Installation and MCP availability have not been verified."
    else:
        install_message(progress, "Installer downloaded; download-only mode did not open it.")
    return result
