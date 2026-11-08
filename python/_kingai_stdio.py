"""Private synchronous MCP stdio transport; no browser or membership logic."""

import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading


class KingAIError(RuntimeError):
    def __init__(self, details):
        self.details = details
        self.code = details.get("code", "KINGAI_ERROR")
        super().__init__(details.get("message") or details.get("error") or self.code)


def failure(code, message, **details):
    return KingAIError({"code": code, "message": message, **details})


def child_environment(*, language, file_roots, download_dir, artifact_dir):
    # Do not copy Agent credentials, Python/Node injection flags or API tokens.
    allowed = {"systemroot", "windir", "systemdrive", "comspec", "pathext",
               "programfiles", "programfiles(x86)", "programw6432", "programdata",
               "userprofile", "appdata", "localappdata", "homedrive", "homepath",
               "username", "userdomain", "temp", "tmp", "home", "lang", "lc_all",
               "lc_ctype", "tmpdir", "display", "wayland_display", "xdg_runtime_dir"}
    env = {key: value for key, value in os.environ.items() if key.lower() in allowed}
    if os.name == "nt":
        root = env.get("SystemRoot") or os.environ.get("SystemRoot", r"C:\Windows")
        env["PATH"] = os.pathsep.join([os.path.join(root, "System32"), root])
    else:
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    if language is not None:
        if not isinstance(language, str):
            raise ValueError("language must be a string")
        env["KINGAI_MCP_LANGUAGE"] = language
    for key, value in (("KINGAI_MCP_DOWNLOAD_DIR", download_dir),
                       ("KINGAI_MCP_ARTIFACT_DIR", artifact_dir)):
        if value is not None:
            path = Path(value)
            if not path.is_absolute():
                raise ValueError(key + " must be an absolute path")
            env[key] = str(path)
    if file_roots is not None:
        if isinstance(file_roots, (str, bytes)):
            raise ValueError("file_roots must be a sequence of absolute paths")
        roots = [Path(value) for value in file_roots]
        if len(roots) > 128 or any(not p.is_absolute() or ";" in str(p) for p in roots):
            raise ValueError("file_roots must contain at most 128 absolute paths without ';'")
        env["KINGAI_MCP_FILE_ROOTS"] = ";".join(map(str, roots))
    return env


class StdioTransport:
    # Bounded JSON lines: oversized or non-protocol stdout is a transport failure.
    MAX_MESSAGE = 32 * 1024 * 1024
    VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}

    def __init__(self, executable, env, timeout):
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        path = Path(executable).expanduser()
        if not path.is_absolute() or not path.is_file():
            raise ValueError("mcp_executable must identify an existing absolute executable path")
        if os.name == "nt" and path.suffix.lower() != ".exe":
            raise ValueError("mcp_executable must be an .exe, not a shell script")
        self.timeout = timeout
        self._state = threading.Lock()
        self._requests = threading.RLock()
        self._pending = {}
        self._next_id = 0
        self._closed = False
        self._dead = None
        self._writes = queue.Queue(maxsize=64)
        self._process = subprocess.Popen(
            [str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=None, env=env, cwd=str(path.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            close_fds=True, bufsize=0,
        )
        self._reader = threading.Thread(target=self._read, name="kingai-mcp-reader", daemon=True)
        self._writer = threading.Thread(target=self._write, name="kingai-mcp-writer", daemon=True)
        self._reader.start()
        self._writer.start()
        try:
            info = self.request("initialize", {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "kingai-python", "version": "0.3.4"},
            }, tool=False)
            if not isinstance(info, dict) or info.get("protocolVersion") not in self.VERSIONS:
                raise failure("MCP_VERSION_MISMATCH", "The installed MCP server negotiated an unsupported protocol version")
            if not isinstance(info.get("capabilities"), dict) or "tools" not in info["capabilities"]:
                raise failure("MCP_TOOLS_UNAVAILABLE", "The installed MCP server does not advertise tools")
            self.server_info = info
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except BaseException:
            self.close()
            raise

    def _send(self, message):
        raw = json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(raw) > self.MAX_MESSAGE:
            raise ValueError("MCP message exceeds the 32 MiB limit")
        with self._state:
            if self._closed or self._dead is not None:
                raise failure("MCP_DISCONNECTED", "The MCP connection is closed")
            try:
                self._writes.put_nowait(raw)
            except queue.Full as error:
                raise failure("MCP_QUEUE_FULL", "The MCP output queue is full; this request was not queued") from error

    def _write(self):
        while True:
            raw = self._writes.get()
            if raw is None:
                return
            with self._state:
                if self._closed or self._dead is not None:
                    return
            # Unbuffered pipes may write only part of a large message.
            try:
                remaining = memoryview(raw)
                while remaining:
                    written = self._process.stdin.write(remaining)
                    if not written:
                        raise OSError("MCP stdin closed")
                    remaining = remaining[written:]
            except (OSError, ValueError):
                self._fail(failure("MCP_DISCONNECTED", "MCP stdin closed or a pipe write failed"))
                return

    def _fail(self, reason):
        with self._state:
            self._dead = reason
            pending = list(self._pending.values())
            self._pending.clear()
        for target in pending:
            target.put(reason)

    def _read(self):
        try:
            while True:
                raw = self._process.stdout.readline(self.MAX_MESSAGE + 1)
                if not raw:
                    break
                if len(raw) > self.MAX_MESSAGE or not raw.endswith(b"\n"):
                    raise ValueError("Invalid MCP message length or delimiter")
                message = json.loads(raw.decode("utf-8"))
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ValueError("Invalid JSON-RPC message")
                if "method" in message:
                    # No sampling/elicitation capabilities are advertised.
                    if "id" in message:
                        if message["method"] == "ping":
                            reply = {"result": {}}
                        else:
                            reply = {"error": {"code": -32601, "message": "Client method not supported"}}
                        self._send({"jsonrpc": "2.0", "id": message["id"], **reply})
                    continue
                identifier = message.get("id")
                if not isinstance(identifier, int) or isinstance(identifier, bool):
                    raise ValueError("Invalid MCP response id")
                if ("result" in message) == ("error" in message):
                    raise ValueError("Invalid MCP response envelope")
                with self._state:
                    target = self._pending.pop(identifier, None)
                if target is not None:
                    target.put(message)
        except (OSError, ValueError, TypeError, KingAIError):
            self._fail(failure("MCP_DISCONNECTED", "MCP output closed or contained an invalid protocol message"))
            return
        self._fail(failure("MCP_DISCONNECTED", "The MCP server exited or closed stdout"))

    def request(self, method, params, *, tool):
        # One complete tools/call per client. Runtime retains its own per-session locks.
        with self._requests:
            with self._state:
                if self._closed or self._dead is not None:
                    raise failure("MCP_DISCONNECTED", "The MCP connection is closed; create a new KingAI client")
                self._next_id += 1
                identifier = self._next_id
                target = queue.Queue()
                self._pending[identifier] = target
            try:
                self._send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
                try:
                    response = target.get(timeout=self.timeout)
                except queue.Empty as error:
                    raise failure("OUTCOME_UNKNOWN" if tool else "MCP_TIMEOUT",
                                  "MCP response timed out; no request was retried. Inspect session state before repeating an action.",
                                  mcpRequestId=identifier, outcomeUnknown=tool) from error
                if isinstance(response, KingAIError):
                    raise failure("OUTCOME_UNKNOWN" if tool else response.code,
                                  "MCP connection lost; no request was retried. Inspect session state before repeating an action.",
                                  mcpRequestId=identifier, outcomeUnknown=tool) from response
                if "error" in response:
                    raise failure("MCP_RPC_ERROR", "MCP returned a JSON-RPC error",
                                  rpcError=response["error"], mcpRequestId=identifier, outcomeUnknown=tool)
                return response["result"]
            except (OSError, KingAIError) as error:
                if isinstance(error, KingAIError):
                    raise
                self._fail(failure("MCP_DISCONNECTED", "MCP pipe write failed"))
                raise failure("OUTCOME_UNKNOWN" if tool else "MCP_DISCONNECTED",
                              "MCP pipe write failed; no request was retried.",
                              mcpRequestId=identifier, outcomeUnknown=tool) from error
            finally:
                with self._state:
                    self._pending.pop(identifier, None)

    def close(self):
        with self._state:
            if self._closed:
                return
            self._closed = True
        self._fail(failure("MCP_DISCONNECTED", "The client was closed"))
        # Close stdio first; terminate only this owned MCP process if it fails
        # to exit. Never terminate Runtime, browser processes or a process tree.
        try:
            self._process.stdin.close()
        except OSError:
            pass
        try:
            self._writes.put_nowait(None)
        except queue.Full:
            pass
        try:
            self._process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired as error:
                    raise failure("MCP_SHUTDOWN_FAILED", "The owned MCP process did not exit after termination") from error
        self._reader.join(timeout=1)
        self._writer.join(timeout=1)
        if not self._reader.is_alive():
            self._process.stdout.close()


def decode_tool(result):
    """Decode the actual KingAI envelope; never call JSON errors an execution timeout."""
    if not isinstance(result, dict):
        raise failure("INVALID_TOOL_RESPONSE", "MCP tool returned a non-object result", outcomeUnknown=True)
    envelope = result.get("structuredContent")
    if not isinstance(envelope, dict) or type(envelope.get("ok")) is not bool:
        blocks = result.get("content", [])
        if not isinstance(blocks, list):
            blocks = []
        texts = [part["text"] for part in blocks
                 if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)]
        try:
            envelope = json.loads("\n".join(texts))
        except ValueError:
            envelope = None
    if isinstance(envelope, dict) and type(envelope.get("ok")) is bool:
        if envelope["ok"] is False:
            raise KingAIError(envelope)
        if not result.get("isError", False):
            return envelope.get("result")
    if result.get("isError", False):
        raise failure("MCP_TOOL_ERROR", "MCP reported a tool error", mcpResult=result)
    raise failure("INVALID_TOOL_RESPONSE", "MCP returned no valid KingAI result envelope; inspect state before repeating the operation",
                  outcomeUnknown=True, mcpResult=result)
