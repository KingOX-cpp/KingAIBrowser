# Troubleshooting / 故障排查

## Start with read-only diagnostics / 先运行只读诊断

```powershell
# Python package installed
kingai-browser doctor
# Equivalent without relying on the console-script PATH
python -m kingai_browser doctor
# Node.js source checkout
node js/cli.mjs doctor
```

If both packages are installed, the console command name may resolve to either package. Use the explicit Python/Node command to identify the implementation. Add `--executable ABSOLUTE_PATH` for a specific installation.

Report fields: client version, discovered MCP executable, server version, actual tool names, missing recommended tools and optional sdk_info. The command only performs discovery, MCP initialization, tools/list and optional sdk_info. It does not start Runtime/browser, log in, create profiles or repair anything. Login is reported as unknown because the current contract exposes no independent read-only authentication probe. Runtime compatibility remains unverified.

诊断报告中的连接成功只说明 MCP 可连接，不代表已登录、会员有效或 Runtime 配套。登录与授权错误仍以实际受保护操作的返回为准。旧 MCP 缺少 sdk_info 会显示兼容提示，而不是把它当成安装损坏。

## MCP_NOT_FOUND / MCP_NOT_INSTALLED

Pass the installed **KingAIMcpServer.exe**, not KingAIBrowser.exe. Verify KingAIRuntime.exe is beside it. Open the current Manager once to refresh the installation record, or set KINGAI_MCP_EXECUTABLE explicitly. No disk scanning or automatic executable download is performed.

检查路径与配套 Runtime；不要把另一目录的旧 MCP 与新 Runtime 混用。

## Startup failure or missing DLL / 启动失败与 DLL 缺失

Child-process stderr is now forwarded to the caller's stderr, separately from MCP stdout. Capture local terminal stderr when investigating startup failures; it may contain sensitive information, so redact it before sharing. The SDK does not persist it or insert it into diagnostic JSON. Native loader failures can appear in Windows dialogs rather than stderr. A missing VCRUNTIME140.dll requires the appropriate Microsoft VC++ runtime or a compatible browser distribution; doctor does not install one.

诊断提示只是排查方向，不是对 DLL 或权限故障的自动定论。

## RUNTIME_ELEVATION_MISMATCH

Follow the message about closing environment browsers, Manager and MCP, then allow the old Runtime to exit before reopening normally. Do not elevate the Manager as a workaround or kill active browser processes to force a version change. RID-500 desktop startup behavior belongs to the installed native components and cannot be repaired by this SDK.

## Default environment missing / 默认环境不存在

launch() without an ID selects the existing unique saved 默认环境. List profiles and supply a real profile ID, or explicitly create the default profile yourself. The SDK never silently creates a temporary replacement.

## Duplicate name / 环境重名

Profile names ignore surrounding whitespace and English case when checking uniqueness. Choose a unique name or explicitly select an existing profile by ID; do not assume a duplicate-name error means creation failed before any earlier operation.

## PAGE_NOT_VISIBLE

Restore the browser window and activate the intended tab. Use browser_wait to check visibility. Do not replay a previous click merely because its subsequent observation failed.

## Version mismatch / 版本不匹配

Update MCP and Runtime as a compatible set through the browser distribution. SDK installation alone does not update native components. sdk_info describes MCP capabilities; runtimeVerified:false is not an error and does not prove Runtime compatibility. The CLI info command falls back to basic server metadata when sdk_info is absent.

## Timeout / RESULT_TOO_LARGE

Neither implies a preceding side effect did not happen. Inspect state before making another input. Limit fields, page read-only results or use an explicit evaluation preview. Never retry a form submission automatically to obtain a smaller response.

## Java and Go diagnostics / Java 与 Go 用户如何自检

Doctor currently ships through the Python/Node CLI only. Java/Go users with Node installed can run `node js/cli.mjs doctor --executable D:\Apps\KingAIBrowser\KingAIMcpServer.exe` from this checkout after installing js/ dependencies. Alternatively install the Python SDK and run `python -m kingai_browser doctor --executable PATH`. This does not make Python/Node a runtime dependency of the Java/Go SDKs. If neither is installed, inspect Java api.tools()/api.serverInfo or Go api.Tools(ctx) and stderr directly; there is no native Java/Go doctor CLI yet.

## Connection ownership / 连接归属

launch() returns a session owning its new client. Python context exit and Java try-with-resources detach and release the owned client while preserving the browser. Non-owned session context/resource exit is a no-op. Explicit browser-close methods remain available: Python close_browser()/close(), Node closeBrowser()/close(), Java closeBrowser(), Go CloseBrowser()/Close(). Java Session.close() is automatic resource cleanup, not browser shutdown. detach() preserves the window and releases an owned client; disconnect() only disconnects the owned client. For sessions created through an explicitly constructed client, close that client yourself.

本轮新增诊断与入口未运行构建、检查、测试或实机验证；需要 review 后另行授权验证。

After detach/disconnect or automatic owned-session cleanup, the original session cannot close the retained window. Use Manager, or discover its real active session from a new client and attach explicitly if authorized. Java closeBrowser() reports SESSION_DISCONNECTED for a closed client, never null; automatic Session.close() remains a no-op after cleanup.
