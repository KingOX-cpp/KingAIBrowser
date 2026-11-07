"""Read-only installation diagnostics. Never starts a browser or changes login."""
from _kingai_discovery import discover_mcp


def doctor(executable=None, *, client_factory=None, client_version="0.3.0"):
    if client_factory is None:
        from kingai_browser import KingAI
        client_factory = KingAI
    report = {
        "clientVersion": client_version, "status": "ok", "checks": [],
        "login": {"status": "unknown", "reason": "No read-only authentication tool is exposed by this SDK contract"},
        "runtime": "not_verified", "stderr": "forwarded_to_parent_stderr",
    }
    try:
        path = discover_mcp(executable)
        report["mcpExecutable"] = path
        with client_factory(path, timeout=15) as api:
            report["server"] = api.server_info
            names = sorted(tool["name"] for tool in api.tools())
            report["tools"] = names
            report["missingRecommendedTools"] = [name for name in
                ("browser_start", "browser_query", "profiles_list", "sdk_info") if name not in names]
            if "sdk_info" in names:
                report["api"] = api.info()
            else:
                report["checks"].append("This older MCP does not expose sdk_info; existing tools may still work")
            if report["missingRecommendedTools"]:
                report["status"] = "warning"
            report["checks"].append("MCP handshake and tools/list completed; browser and Runtime were not started")
    except Exception as error:
        report["status"] = "error"
        report["error"] = {"code": getattr(error, "code", "DOCTOR_FAILED"), "message": str(error)}
        report["checks"].extend([
            "Verify the installed MCP path and its sibling Runtime executable",
            "Inspect parent stderr and any Windows loader dialog for missing VC++ runtime DLLs",
            "For RUNTIME_ELEVATION_MISMATCH, follow the Runtime permissions troubleshooting guide; do not force-kill active browsers",
        ])
    return report
