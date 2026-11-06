"""Locate an installed MCP; never scan disks, search PATH or download a browser."""
import json
import os
from pathlib import Path
import sys

from _kingai_stdio import failure


def discover_mcp(executable=None):
    selected = executable if executable is not None else os.environ.get("KINGAI_MCP_EXECUTABLE")
    if selected is None:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            manifest = Path(base) / "KingAIBrowser/sdk-installation.json" if base else None
        elif sys.platform == "darwin":
            manifest = Path.home() / "Library/Application Support/KingAIBrowser/sdk-installation.json"
        else:
            manifest = Path.home() / ".config/KingAIBrowser/sdk-installation.json"
        if manifest is not None and manifest.is_file():
            try:
                with manifest.open("rb") as handle:
                    raw = handle.read(65537)
                if len(raw) > 65536:
                    raise ValueError("Discovery record too large")
                record = json.loads(raw.decode("utf-8"))
                if not isinstance(record, dict) or record.get("schemaVersion") != 1:
                    raise ValueError("Unsupported discovery record")
                selected = record["mcpExecutable"]
                if not isinstance(selected, str):
                    raise ValueError("Invalid executable path")
            except (OSError, ValueError, KeyError) as error:
                raise failure("MCP_DISCOVERY_INVALID", "Open the current Manager to refresh SDK discovery, or pass mcp_executable explicitly") from error
    if selected is None:
        raise failure("MCP_NOT_FOUND", "Open the current Manager once, set KINGAI_MCP_EXECUTABLE, or pass mcp_executable with the absolute MCP executable path")
    path = Path(selected).expanduser()
    expected = "KingAIMcpServer.exe" if os.name == "nt" else "KingAIMcpServer"
    runtime = "KingAIRuntime.exe" if os.name == "nt" else "KingAIRuntime"
    if not path.is_absolute() or path.name.lower() != expected.lower():
        raise failure("MCP_PATH_INVALID", "Specify the absolute KingAIMcpServer executable path")
    if not path.is_file() or not path.with_name(runtime).is_file():
        raise failure("MCP_NOT_INSTALLED", "MCP or its sibling Runtime is missing; reopen the updated Manager or specify a complete installation")
    return str(path.resolve())
