# KingAI Go SDK guide

English | [简体中文](README.zh-CN.md) | [Project / 项目](../README.md)

**SDK 0.3.0 · MIT · Go 1.24+**

Calls the installed KingAI MCP over stdio. No HTTP service or Playwright is required. Install the browser, sign in and use matching MCP/Runtime components first.

Lifecycle update: Python launch contexts and Java automatic Session resource cleanup detach and preserve windows. Explicit browser shutdown uses Python close()/close_browser(), Node close()/closeBrowser(), Java closeBrowser(), or Go Close()/CloseBrowser(). New ownership cases and launch/doctor changes are unexecuted; the historical 17-test result does not cover them.

After disconnecting, the original Session can no longer operate the retained window. Close it in Manager, or discover the real active session through a new client and explicitly attach if authorized. No automatic reconnection occurs. Java closeBrowser() throws SESSION_DISCONNECTED if its client is closed.

Four-language overview: [launch, explicit clients and Agent facades](../docs/SDK_ENTRY_POINTS.md). BrowserAutomation exists in Python/Node; Java/Go currently expose clients and sessions without that facade. See the matrix before choosing an entry point.

## Download the browser installer

Supports Windows Intel/AMD x64 and Apple Silicon macOS only, not Windows ARM, 32-bit Windows or Intel Mac. Each language has a native downloader. Explicit install calls can download and open the installer/DMG; finish its UI steps yourself. This is not silent installation.

```go
// Inside a function returning error.
result, err := kingai.Install(ctx, kingai.InstallOptions{DownloadOnly: true})
if err != nil { return err }
fmt.Println(result.Status, result.InstallerPath)
```

Windows downloads default to D:. The download directory is not the browser installation directory. TLS verification stays enabled; invalid/mismatched IP certificates fail. Supply a trusted SHA-256 to verify the payload. After installation, open Manager, sign in and run doctor. No installer was downloaded or executed, and no build/check/test was run in this change.

[Full installation guide](../INSTALLATION.md)

## Quick entry: launch

After installation and login, this entry discovers/connects MCP and starts a saved profile. The default must already exist; no missing-profile fallback is created.

```go
browser, err := kingai.Launch(ctx, kingai.Options{}, "")
if err != nil { return err }
defer browser.Detach(ctx)
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
page, err := browser.Read(ctx)
if err != nil { return err }
fmt.Println(page)
// Pass a real saved profile ID instead of "" to select it explicitly.
```

The returned session owns its new client. Close closes the browser and releases MCP; detach preserves the browser and releases MCP; disconnect only releases the connection. Explicit-client APIs remain available.

[Troubleshooting / 故障排查](../TROUBLESHOOTING.md)

## Installation and discovery

```powershell
Use the local go.mod replace shown below.
```

```go
require github.com/KingOX-cpp/KingAIBrowser/go v0.0.0
replace github.com/KingOX-cpp/KingAIBrowser/go => D:/code/KingAIBrowser/go
```

Import `kingai "github.com/KingOX-cpp/KingAIBrowser/go"`. `v0.0.0` is a local-replace placeholder.

```powershell
$env:KINGAI_MCP_EXECUTABLE = 'D:\Apps\KingAIBrowser\KingAIMcpServer.exe'
```

Replace the example path. Discovery uses an explicit SDK option, then the environment variable, then the Manager record. Do not pass the main browser executable. Keep caches, temporary files and outputs on D:. Public registry packages are not published.

## Start with a complete example

[Examples and prerequisites / 示例与前提](../examples/README.md) · [API recipes / 接口调用手册](../docs/API_EXAMPLES.md)

```powershell
# From repository root / 在仓库根目录，另开终端启动演示网页
python -m http.server 8765 --bind 127.0.0.1 --directory examples
# Then run in another terminal / 然后另开终端执行
cd go
go run ./examples/workflow --live
```

The complete workflow lists/creates/configures profiles, inspects DOM, queries refs, fills fields, clicks and independently confirms the result. Keep the window visible. Newly created profiles are retained.

## Calling pattern and results

```go
// Inside a function returning error; ctx is context.Context.
// 函数体片段，需导入 context、fmt 和下方 module。
api, err := kingai.Connect(ctx, kingai.Options{})
if err != nil { return err }
defer api.Close()
profiles, err := api.Profiles(ctx)
if err != nil { return err }
fmt.Println(profiles)
browser, err := api.Start(ctx, nil) // Existing 默认环境
if err != nil { return err }
if _, err = browser.NewTab(ctx, "http://127.0.0.1:8765/demo.html"); err != nil { return err }
elements, err := browser.Query(ctx, kingai.Arguments{"selector": "#name", "include_html": true})
if err != nil { return err }
fmt.Println(elements)
_, err = browser.Detach(ctx)
return err
```

`profileId` identifies saved environments; `sessionId` identifies a running session; `targetId` identifies a tab; `ref` identifies an observed element. / 四类 ID 分别代表环境、会话、标签和已观察元素，不可混用。

## API category map

| Category / 类别 | MCP tools / 工具 | Usage / 用途 |
| --- | --- | --- |
| Profiles / 环境 | `profiles_list`, `profiles_get`, `profiles_create`, `profiles_update`, `profiles_delete` | List summaries; create, inspect, configure a closed profile, explicitly delete. / 获取摘要、创建、读取、修改已关闭环境、显式删除。 |
| Sessions / 会话 | `browser_start`, `browser_sessions_list`, `browser_attach`, `browser_detach`, `browser_close` | Start by profile ID, discover active sessions, attach or detach. Close is destructive. / 按环境 ID 启动、查找和接入会话，区分断开与关闭。 |
| Tabs / 标签页 | `tabs_list`, `tabs_new`, `tabs_activate`, `tabs_close`, `browser_navigate` | Use returned targetId; activate before input. / 使用返回的 targetId，输入前激活目标标签。 |
| DOM / 页面 | `browser_read`, `browser_snapshot`, `browser_query`, `browser_wait` | Read text, inspect bounded DOM, obtain refs, wait for explicit conditions. / 读取文本、观察 DOM、取得 ref、等待明确条件。 |
| Input / 输入 | `browser_click`, `browser_fill`, `browser_type`, `browser_key`, `browser_scroll`, `browser_hover` | Fill replaces text; type appends. Query refs before action. / fill 替换，type 追加；先查询再操作。 |
| JavaScript / 求值 | `browser_evaluate` | Raw evaluation preserves results; preview is bounded and may truncate. / 原始求值与显式预览不同，预览可能截断。 |
| Artifacts / 产物 | `browser_screenshot`, `browser_pdf`, `browser_upload`, `browser_download` | Configure artifact/download roots and permitted upload paths. / 配置产物目录、下载目录和上传权限。 |
| State / 状态 | `cookies_list`, `storage_get` | Inspect local site state; never publish cookies or secrets. / 查看站点状态，不公开 Cookie 或秘密。 |
| Skills / 工作流 | `skills_list`, `skill_describe`, `skill_run`, `skill_status`, `skill_cancel`, `skill_runs_list` | Discover parameters before starting; poll returned run ID. / 先发现参数，启动后用真实 run ID 查询。 |
| Discovery / 工具发现 | `sdk_info`, `tools/list`, `runtime_request_status` | Installed schemas are authoritative; Runtime IDs are not JSON-RPC IDs. / 以安装版 schema 为准，区分 Runtime ID 与 JSON-RPC ID。 |

Every installed tool is available through generic `call` / `Call`; convenience methods differ by language. Use the recipes for exact argument examples and inspect `tools/list` for required fields. / 所有安装版工具都能经通用调用访问，便利方法并非每种语言完全相同；参数示例见手册，必填项以安装版 schema 为准。

## Lifecycle, errors and permissions

- Client close disconnects MCP; session close closes the browser. Detach keeps the browser available. / 客户端关闭、会话断开和浏览器关闭含义不同。
- Default start requires an existing unique 默认环境; it does not create one. / 默认启动不会自动创建缺失环境。
- Update only closed profiles; deletion requires explicit confirmation and removes persistent data. / 更新前关闭环境；删除需确认且会移除持久数据。
- Side effects are not automatically retried after timeout or observation failure. / 超时和观察失败不自动重放输入。
- Humanize needs valid entitlement; examples explicitly use false for basic form interaction. / 拟人化需要有效权益，演示显式关闭。
- PAGE_NOT_VISIBLE requires restoring the window and selecting the intended tab. / 页面不可见时恢复窗口并激活标签。
- Call sequences use one selected tab; serialize multi-step workflows. / 多步操作串行，不是 Playwright 多 Page 模型。

## Test scope and license

[SAMPLES.md](../SAMPLES.md) records earlier fixture tests. New examples, documentation and renames have not been built, checked or tested in this task. / 旧模拟测试不代表新增示例已实机验证；本轮未运行构建、检查或测试。

MIT: retain copyright/license and applicable third-party notices. / 允许传播、修改与商用，保留版权、许可及适用的第三方声明。
