"""KingAI Python SDK: the installed MCP server over stdio (Python 3.10+)."""
import atexit
from contextlib import contextmanager
import os
import threading

from _kingai_discovery import discover_mcp
from _kingai_stdio import KingAIError, StdioTransport, child_environment, decode_tool, failure

__all__ = ["KingAI", "KingAIError", "BrowserSession", "discover_mcp"]
__version__ = "0.3.0"


class KingAI:
    """A lazy, owned MCP connection. close() disconnects; it does not close browsers."""

    def __init__(self, mcp_executable=None, *, timeout=360, language=None,
                 file_roots=None, download_dir=None, artifact_dir=None):
        self._executable = mcp_executable
        self._timeout = timeout
        self._env = child_environment(language=language, file_roots=file_roots,
                                      download_dir=download_dir, artifact_dir=artifact_dir)
        self._lock = threading.RLock()
        self._transport = None
        self._closed = False
        self._cleanup = self.close
        atexit.register(self._cleanup)

    def connect(self):
        with self._lock:
            if self._closed:
                raise failure("CLIENT_CLOSED", "Create a new KingAI client after close()")
            if self._transport is None:
                executable = discover_mcp(self._executable)
                try:
                    self._transport = StdioTransport(executable, self._env, self._timeout)
                except OSError as error:
                    raise failure("MCP_START_FAILED", "Could not start the installed MCP executable", reason=str(error)) from error
            return self

    @property
    def server_info(self):
        self.connect()
        return self._transport.server_info

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._transport is not None:
                self._transport.close()
            atexit.unregister(self._cleanup)

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @contextmanager
    def exclusive(self):
        """Serialize a multi-step sequence against other threads using THIS client."""
        with self._lock:
            yield self

    def tools(self):
        with self._lock:
            self.connect()
            tools, cursors = [], set()
            cursor = None
            while True:
                result = self._transport.request("tools/list", {} if cursor is None else {"cursor": cursor}, tool=False)
                if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                    raise failure("INVALID_TOOL_RESPONSE", "MCP tools/list returned an invalid result")
                tools.extend(result["tools"])
                cursor = result.get("nextCursor")
                if cursor is None:
                    return tools
                if not isinstance(cursor, str) or cursor in cursors:
                    raise failure("INVALID_TOOL_RESPONSE", "MCP tools/list returned an invalid or repeated cursor")
                cursors.add(cursor)

    def call(self, name, arguments=None):
        """Call ANY tool advertised by MCP, preserving its parameter/result fields."""
        if not isinstance(name, str) or not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name):
            raise ValueError("Invalid tool name")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a dict")
        with self._lock:
            self.connect()
            result = self._transport.request("tools/call", {"name": name, "arguments": arguments}, tool=True)
            return decode_tool(result)

    def profiles(self):
        return self.call("profiles_list")

    def info(self):
        return self.call("sdk_info")

    def profile(self, profile_id):
        return self.call("profiles_get", {"profile_id": profile_id})

    def create_profile(self, name, *, group_name=None, language=None):
        args = {"name": name}
        if group_name is not None:
            args["group_name"] = group_name
        if language is not None:
            args["language"] = language
        return self.call("profiles_create", args)

    def update_profile(self, profile_id, *, name=None, group_name=None, patch=None):
        args = {"profile_id": profile_id}
        for key, value in (("name", name), ("group_name", group_name), ("patch", patch)):
            if value is not None:
                args[key] = value
        return self.call("profiles_update", args)

    def delete_profile(self, profile_id, *, confirm=False):
        return self.call("profiles_delete", {"profile_id": profile_id, "confirm": confirm})

    def sessions(self):
        return self.call("browser_sessions_list")

    def start(self, profile_id=None, *, headless=False, temporary=False):
        options = {"headless": headless, "temporary": temporary}
        if profile_id is not None:
            options["profile_id"] = profile_id
        info = self.call("browser_start", options)
        if not isinstance(info, dict) or not isinstance(info.get("sessionId"), str) or not info["sessionId"]:
            raise failure("INVALID_TOOL_RESPONSE", "browser_start returned no sessionId; inspect sessions before restarting", outcomeUnknown=True)
        return BrowserSession(self, info["sessionId"], info)

    def attach(self, session_id):
        info = self.call("browser_attach", {"session_id": session_id})
        return BrowserSession(self, session_id, info)

    def request_status(self, request_id):
        """Requires a RUNTIME request ID from the backend, not an MCP JSON-RPC ID."""
        return self.call("runtime_request_status", {"request_id": request_id})

    def skills(self):
        return self.call("skills_list")

    def describe_skill(self, skill_id):
        return self.call("skill_describe", {"skill_id": skill_id})

    def run_skill(self, profile_id, skill_id, **options):
        return self.call("skill_run", {**options, "profile_id": profile_id, "skill_id": skill_id})

    def skill_status(self, run_id):
        return self.call("skill_status", {"run_id": run_id})

    def cancel_skill(self, run_id):
        return self.call("skill_cancel", {"run_id": run_id})

    def skill_runs(self):
        return self.call("skill_runs_list")


class BrowserSession:
    """One browser session, with one selected tab. This is not a Playwright Page."""
    def __init__(self, client, session_id, info=None):
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string")
        self.client, self.session_id, self.info = client, session_id, info
        self._owns_client = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._owns_client and not self.client._closed:
            try:
                self.detach()
            except Exception as cleanup_error:
                if exc_value is None:
                    raise
                # Preserve the original body failure if cleanup also fails.
                if hasattr(exc_value, "add_note"):
                    exc_value.add_note("Session detach also failed: " + str(cleanup_error))

    def disconnect(self):
        """Disconnect an owned launch connection without closing the browser."""
        if not self._owns_client:
            raise ValueError("This session does not own its client; close the client explicitly")
        self.client.close()

    def call(self, name, *, observe=False, **arguments):
        # Cover action AND observation; another thread must not switch tabs
        # between the input and its attributed observation.
        with self.client.exclusive():
            result = self.client.call(name, {**arguments, "session_id": self.session_id})
            if observe:
                from _kingai_automation import observe_operation
                return observe_operation(self, name, result)
            return result

    def evaluate_preview(self, expression, **options):
        """Opt-in bounded result preview. The original expression runs once."""
        from _kingai_automation import BrowserAutomation
        expression = BrowserAutomation._bounded_evaluation(expression, options.get("await_promise", True))
        return self.call("browser_evaluate", expression=expression, **options)

    def tabs(self):
        return self.call("tabs_list")

    def new_tab(self, url=None):
        return self.call("tabs_new", **({"url": url} if url is not None else {}))

    def activate_tab(self, target_id):
        return self.call("tabs_activate", target_id=target_id)

    def close_tab(self, target_id):
        return self.call("tabs_close", target_id=target_id)

    def goto(self, url):
        return self.call("browser_navigate", url=url)

    def read(self, **options):
        return self.call("browser_read", **options)

    def snapshot(self, **options):
        return self.call("browser_snapshot", **options)

    def query(self, **options):
        return self.call("browser_query", **options)

    def click(self, selector=None, **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_click", **options)

    def fill(self, selector=None, text="", **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_fill", text=text, **options)

    def type(self, selector=None, text="", **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_type", text=text, **options)

    def evaluate(self, expression, **options):
        return self.call("browser_evaluate", expression=expression, **options)

    def wait(self, **options):
        return self.call("browser_wait", **options)

    def screenshot(self, **options):
        return self.call("browser_screenshot", **options)

    def scroll(self, delta_y, **options):
        return self.call("browser_scroll", delta_y=delta_y, **options)

    def key(self, key, **options):
        return self.call("browser_key", key=key, **options)

    def hover(self, selector=None, **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_hover", **options)

    def pdf(self, **options):
        return self.call("browser_pdf", **options)

    def cookies(self):
        return self.call("cookies_list")

    def storage(self, **options):
        return self.call("storage_get", **options)

    def upload(self, paths, selector=None, **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_upload", paths=[os.fspath(path) for path in paths], **options)

    def download(self, selector=None, **options):
        if selector is not None:
            options["selector"] = selector
        return self.call("browser_download", **options)

    def detach(self):
        try:
            return self.call("browser_detach")
        finally:
            if self._owns_client:
                self.client.close()

    def close(self):
        """Explicitly close the browser; connection cleanup does not call this."""
        try:
            return self.call("browser_close")
        finally:
            if self._owns_client:
                self.client.close()

    def close_browser(self):
        """Explicit browser-close alias, distinct from automatic context cleanup."""
        return self.close()


def launch(profile_id=None, *, headless=False, temporary=False, **client_options):
    """Connect and open a saved environment; the returned session owns its client.

    Omit profile_id for the existing unique default profile. No missing-profile
    fallback is created. Context exit detaches and preserves the browser.
    close()/close_browser() explicitly close it; detach() preserves it.
    """
    api = KingAI(**client_options)
    try:
        browser = api.start(profile_id, headless=headless, temporary=temporary)
        browser._owns_client = True
        return browser
    except BaseException:
        api.close()
        raise


__all__.append("launch")

from _kingai_installer import install
__all__.append("install")

# Optional high-level action/observation facade; no OpenManus dependency.
from _kingai_automation import BrowserAutomation
__all__.append('BrowserAutomation')
from _kingai_async import AsyncKingAI, AsyncBrowserSession
__all__.extend(['AsyncKingAI', 'AsyncBrowserSession'])


def main():
    """SDK diagnostics and explicit installer download/launch commands."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description="KingAI SDK diagnostics and installer management")
    parser.add_argument("command", choices=["info", "tools", "profiles", "doctor", "install"], nargs="?", default="info")
    parser.add_argument("--executable", help="Absolute installed MCP executable path")
    parser.add_argument("--download-dir", help="Absolute installer download directory, not browser installation directory")
    parser.add_argument("--download-only", action="store_true", help="Download without opening the installer")
    parser.add_argument("--sha256", help="Trusted expected installer checksum")
    parser.add_argument("--no-reuse-existing", action="store_true", help="Download even if MCP discovery already finds an installation")
    args = parser.parse_args()
    if args.command == "install":
        if args.executable:
            parser.error("--executable is for diagnostics; install uses --download-dir")
        try:
            result = install(download_dir=args.download_dir, download_only=args.download_only,
                             sha256=args.sha256, reuse_existing=not args.no_reuse_existing)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as error:
            print(json.dumps({"code": getattr(error, "code", "INSTALL_FAILED"), "message": str(error)}, ensure_ascii=False))
            return 1
    if args.download_dir or args.download_only or args.sha256 or args.no_reuse_existing:
        parser.error("Installer options require the install command")
    if args.command == "doctor":
        from _kingai_doctor import doctor
        report = doctor(args.executable, client_factory=KingAI, client_version=__version__)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] != "error" else 1
    try:
        with KingAI(args.executable) as api:
            if args.command == "info":
                available = {tool["name"] for tool in api.tools()}
                value = {"clientVersion": __version__, "mcp": api.server_info,
                         "api": api.info() if "sdk_info" in available else None,
                         "compatibilityNote": None if "sdk_info" in available else "Older MCP: sdk_info is unavailable; inspect tools for supported capabilities"}
            else:
                value = getattr(api, args.command)()
            print(json.dumps(value, ensure_ascii=False, indent=2))
    except KingAIError as error:
        print(json.dumps(error.details, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


