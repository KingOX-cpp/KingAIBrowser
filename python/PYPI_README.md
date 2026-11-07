# KingAI Browser Python SDK

Python 3.10+ client for KingAI Browser's installed stdio MCP server. Manage saved fingerprint environments and automate pages without Playwright or a separate HTTP service.

[Website](https://www.kingaibrowser.cn/) · [Alternative website](https://kingaibrowser.ccwu.cc/) · [Source and examples](https://github.com/KingOX-cpp/KingAIBrowser) · [Browser releases](https://github.com/KingOX-cpp/KingAIBrowser/releases)

## Install the SDK

```shell
python -m pip install kingai-browser
```

The Python runtime library uses only the standard library. Browser installation and account login are separate from installing the SDK.

## Download the browser

```shell
python -m kingai_browser install
```

Supports Windows Intel/AMD x64 and Apple Silicon macOS only. The explicit install command downloads and opens the Windows installer or macOS DMG; complete the installation UI yourself. It is not a silent installer. Open KingAI Manager and sign in after installation.

For download only:

```python
from kingai_browser import install
result = install(download_only=True)
print(result["status"], result["installerPath"])
```

Windows downloads default to D:\code\KingAIBrowser-downloads; macOS uses ~/Downloads/KingAIBrowser. Set download_dir to an absolute path to change installer storage. It does not select the browser installation folder. HTTPS certificate verification remains enabled; IP certificate mismatches fail. Optional sha256 compares the installer to a trusted checksum supplied by the caller. A calculated hash alone is not authenticity verification.

## Locate MCP and diagnose

The SDK finds MCP using an explicit mcp_executable option, KINGAI_MCP_EXECUTABLE, or the per-user installation record written by a compatible Manager. KingAIMcpServer and KingAIRuntime must be installed together. The browser executable is not the MCP server.

```shell
python -m kingai_browser doctor
```

Doctor reports installation discovery, MCP version and available tools without launching a browser. It does not verify Runtime compatibility or account login. Native stderr is forwarded to your terminal; redact sensitive information before sharing it.

## Open a saved environment

```python
from kingai_browser import launch

with launch() as browser:
    browser.new_tab("https://example.com")
    print(browser.read())
```

The default is the existing unique saved profile named 默认环境. If it does not exist, explicitly select a saved profile with launch(profile_id="actual-profile-id") or create one using the management API. No temporary fallback is created.

Context exit detaches and releases the owned MCP connection while preserving the browser window. Explicit close_browser() closes the browser. After detaching, the original session cannot continue controlling that window; use Manager or explicitly attach a new authorized client to the active session.

## Profiles, DOM and input

```python
from kingai_browser import KingAI

with KingAI() as api:
    print(api.profiles())
    created = api.create_profile("My unique profile", language="en-US")
    profile_id = created["profileId"]
    api.update_profile(profile_id, name="My configured profile")
    browser = api.start(profile_id=profile_id)
    try:
        browser.new_tab("https://example.com")
        print(browser.snapshot(mode="interactive", limit=30))
        print(browser.query(role="link", include_html=True, limit=10))
    finally:
        browser.detach()
```

On a page containing your target input/button, query its DOM and use a freshly observed ref:

```python
matches = browser.query(selector="#name", limit=2)["elements"]
if len(matches) != 1:
    raise RuntimeError("Expected one input")
browser.fill(ref=matches[0]["ref"], text="KingAI", humanize=False)
```

This last fragment requires a live session and a page containing #name; example.com does not contain that input. Full runnable form examples and a local playground are in the source repository.

All installed MCP tools remain available through api.tools() and api.call(name, arguments). AsyncKingAI provides the async interface; BrowserAutomation provides an optional Agent action facade.

## Important behavior

- Update closed profiles only. Deletion requires explicit confirmation and removes saved data.
- Sessions operate on a selected tab. Serialize multi-step input workflows.
- Humanize requires valid account entitlement. Limits apply to concurrent open environments, not individual clicks.
- PAGE_NOT_VISIBLE requires restoring the window and activating the intended tab.
- A dispatched action is not proof of business completion. Independently observe the page result.
- Timeouts and observation errors do not automatically retry side effects.
- evaluate_preview provides bounded output and may truncate results.

Browser download/installation and real-site automation have not been validated as part of the first package publication. Installation/import checks do not establish browser compatibility or anti-detection performance.

## 中文说明

本包提供 Python 同步、异步调用，以及保存环境管理、DOM 观察、点击输入和通用 MCP 工具调用。先安装 SDK，再显式下载并完成浏览器安装、打开管理器登录。默认启动使用已存在的唯一“默认环境”，不会自动创建临时环境。with launch() 退出保留窗口；显式 close_browser() 才关闭浏览器。

完整中英文使用说明、示例和问题反馈请访问上述 GitHub 仓库。Windows 仅支持 Intel/AMD x64，Mac 仅支持 Apple 芯片。

## License

MIT. Retain copyright, license and applicable third-party notices. This package contains client SDK code; third-party notices are included in the distribution.
