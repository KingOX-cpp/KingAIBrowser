"""Installer path regression cases. Downloads use in-memory fake responses."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import _kingai_installer as installer


class FakeResponse(io.BytesIO):
    status = 200
    headers = {"Content-Length": "6", "Content-Type": "application/octet-stream"}


class InstallerPathTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_default_uses_system_temp_without_fixed_drive(self):
        selected = self.root / "system-temp"
        with patch.object(installer.tempfile, "gettempdir", return_value=str(selected)):
            self.assertEqual(installer.default_download_dir(), selected)

    def test_default_does_not_depend_on_localappdata(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(installer.tempfile, "gettempdir", return_value=str(self.root)):
            self.assertEqual(installer.default_download_dir(), self.root)

    def download(self, directory=None):
        opener = Mock()
        opener.open.return_value = FakeResponse(b"MZfake")
        with patch.object(installer, "target", return_value=("windows-x64", "KingAIBrowserSetup.exe")), patch.object(installer, "build_opener", return_value=opener), patch.object(installer.subprocess, "Popen") as launch:
            result = installer.install(download_dir=directory, download_only=True, reuse_existing=False)
        launch.assert_not_called()
        return result

    def test_download_default_stays_in_system_temp(self):
        local = self.root / "system-temp"
        with patch.object(installer.tempfile, "gettempdir", return_value=str(local)):
            result = self.download()
        path = Path(result["installerPath"])
        self.assertTrue(path.is_relative_to(local))
        self.assertEqual(path.read_bytes(), b"MZfake")
        self.assertEqual(result["status"], "downloaded")

    def test_explicit_directory_remains_supported(self):
        selected = self.root / "explicit-downloads"
        result = self.download(selected)
        self.assertTrue(Path(result["installerPath"]).is_relative_to(selected))

    def test_default_opens_installer_ui_without_silent_arguments(self):
        opener = Mock()
        opener.open.return_value = FakeResponse(b"MZfake")
        with patch.object(installer.sys, "platform", "win32"), patch.object(installer, "target", return_value=("windows-x64", "KingAIBrowserSetup.exe")), patch.object(installer, "build_opener", return_value=opener), patch.object(installer.subprocess, "Popen") as launch:
            result = installer.install(download_dir=self.root, reuse_existing=False)
        self.assertEqual(result["status"], "installer_started")
        self.assertEqual(launch.call_args.args[0], [result["installerPath"]])
