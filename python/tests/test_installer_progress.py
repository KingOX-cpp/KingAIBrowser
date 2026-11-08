"""Progress/output regression cases with fake responses; no network or installer UI."""
import contextlib
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import _kingai_installer as installer


class Response(io.BytesIO):
    status = 200
    def __init__(self, headers):
        super().__init__(b"MZfake")
        self.headers = headers


class InstallerProgressTests(unittest.TestCase):
    def download(self, response, progress=True):
        with tempfile.TemporaryDirectory() as directory:
            opener = Mock()
            opener.open.return_value = response
            stderr, stdout = io.StringIO(), io.StringIO()
            with patch.object(installer, "target", return_value=("windows-x64", "KingAIBrowserSetup.exe")), patch.object(installer, "build_opener", return_value=opener), patch.object(installer.subprocess, "Popen") as launch, contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
                result = installer.install(download_dir=Path(directory), download_only=True,
                                           reuse_existing=False, progress=progress)
            launch.assert_not_called()
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(result["status"], "downloaded")
            return stderr.getvalue()

    def test_known_length_progress_stays_on_stderr(self):
        text = self.download(Response({"Content-Length": "6"}))
        self.assertIn("100.0%", text)
        self.assertIn("/s", text)
        self.assertIn("ETA", text)
        self.assertIn("Download complete", text)

    def test_unknown_length_does_not_invent_percentage(self):
        text = self.download(Response({}))
        self.assertIn("unknown total", text)
        self.assertNotIn("100.0%", text)

    def test_programmatic_calls_can_remain_quiet(self):
        self.assertEqual(self.download(Response({"Content-Length": "6"}), progress=False), "")

    def test_slow_download_has_no_ten_minute_total_deadline(self):
        clock = [0]
        class SlowResponse(Response):
            def read1(self, size):
                clock[0] += 700
                return super().read1(size)
        with patch.object(installer.time, "monotonic", side_effect=lambda: clock[0]):
            self.download(SlowResponse({"Content-Length": "6"}), progress=False)
        self.assertGreater(clock[0], 600)

    def test_socket_timeout_must_be_positive(self):
        with patch.object(installer, "target", return_value=("windows-x64", "KingAIBrowserSetup.exe")):
            with self.assertRaises(ValueError):
                installer.install(network_timeout=0)

    def test_socket_timeout_is_forwarded_without_total_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = Mock()
            opener.open.return_value = Response({"Content-Length": "6"})
            with patch.object(installer, "target", return_value=("windows-x64", "KingAIBrowserSetup.exe")), patch.object(installer, "build_opener", return_value=opener):
                installer.install(download_dir=directory, download_only=True, reuse_existing=False, network_timeout=90)
            self.assertEqual(opener.open.call_args.kwargs["timeout"], 90)

    def test_waiting_socket_still_has_periodic_feedback(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True
        stream = Terminal()
        with contextlib.redirect_stderr(stream):
            progress = installer.DownloadProgress(True)
            progress.start()
            try:
                # No bytes arrive while the progress worker remains active.
                threading.Event().wait(1.2)
            finally:
                progress.stop()
        self.assertGreaterEqual(stream.getvalue().count("Connecting:"), 3)
