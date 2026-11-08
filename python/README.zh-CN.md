# KingAI Python 使用说明

[English](README.md) | 简体中文 | [Project / 项目](../README.md)

**SDK 0.3.4 · MIT · Python 3.10+**

**首次使用请先看：[launch、KingAI、BrowserAutomation 详细区别与用法](ENTRY_POINTS.zh-CN.md)**，包含入口选择、完整示例、DOM/状态区别和连接/窗口生命周期速查。[English](ENTRY_POINTS.md)。

本库通过 stdio 调用已安装的 KingAI MCP，不需要 HTTP 服务或 Playwright。先安装浏览器并登录，MCP/Runtime 必须支持所需工具。

生命周期更新：Python launch 上下文和 Java Session 自动资源退出会 detach 并保留窗口。显式关闭分别使用 Python close()/close_browser()、Node close()/closeBrowser()、Java closeBrowser()、Go Close()/CloseBrowser()。新增 ownership、launch、doctor 均未执行验证，历史 17 项测试不覆盖这些改动。

连接释放后，原 Session 对象不能继续操作保留窗口。可在 Manager 中关闭，或由新客户端发现真实会话、在授权允许时显式 attach 后关闭；SDK 不自动重连。Java closeBrowser() 在客户端已关闭时抛 SESSION_DISCONNECTED。

四语言入口总览：[launch、显式客户端和 Agent facade 的区别与用法](../docs/SDK_ENTRY_POINTS.zh-CN.md)。Python/Node 提供 BrowserAutomation，Java/Go 当前未提供同名封装；普通会话与通用 MCP 调用四种语言均支持。

## 浏览器下载安装

支持 Windows Intel/AMD x64 和 Apple 芯片 Mac，不支持 Windows ARM、32 位 Windows 或 Intel Mac。四语言均提供原生下载实现；显式安装命令可下载并打开安装向导/DMG，仍需用户完成安装，不是静默安装。

```powershell
python -m kingai_browser install --download-only
# Download and open the installer UI
python -m kingai_browser install
```

```python
from kingai_browser import install
result = install(download_only=True)
print(result["status"], result["installerPath"])
```

Windows 和 macOS 安装包默认下载到系统临时目录；下载目录不是浏览器安装目录。证书校验保持开启，IP 证书不可信或不匹配会失败；可传可信 SHA-256 校验文件。安装后打开 Manager 登录并运行 doctor。新增下载/安装入口本轮未下载或执行安装包，未运行构建、检查或测试。

[完整安装说明](../INSTALLATION.zh-CN.md)

## 快速入口：launch

普通脚本用 launch()/KingAI 返回的会话调用 query()/snapshot() 获取 DOM。BrowserAutomation 是给 OpenManus 等 Agent 适配层使用的高层动作/状态封装，提供 execute、get_current_state、describe_error 和 close；其状态中的 interactive_elements 是 JSON 字符串形式的快照，不是浏览器持久存储或直接可用的 DOM 数组。详见[入口区别及完整接口示例](../docs/API_EXAMPLES.md)。

完成安装和登录后，下面的入口负责定位 MCP、连接并启动环境。默认只打开已有的唯一“默认环境”，不会自动创建缺失环境。

```python
from kingai_browser import launch

browser = launch()  # Existing unique default environment
try:
    browser.new_tab("https://example.com")
    print(browser.read())
finally:
    browser.detach()
```

返回的会话拥有新客户端。close 关闭浏览器并释放 MCP；detach 保留浏览器并释放 MCP；disconnect 仅释放连接。原有显式客户端 API 保持可用。

[Troubleshooting / 故障排查](../TROUBLESHOOTING.md)

```powershell
python -m kingai_browser doctor
```

只读诊断不启动浏览器；登录态显示 unknown，Runtime 未验证。MCP stderr 转发至终端，不存入报告。旧 MCP 缺少 sdk_info 时 CLI info 仍返回基础信息。

## 安装与定位

```powershell
python -m pip install --cache-dir D:/code/kingai-sdk-cache/pip ./python
```

```powershell
$env:KINGAI_MCP_EXECUTABLE = 'D:\Apps\KingAIBrowser\KingAIMcpServer.exe'
```

示例路径需替换。定位顺序为显式 SDK 参数、环境变量、管理器登记。不能把浏览器主程序当 MCP。Python SDK 0.3.4 已[发布到 PyPI](https://pypi.org/project/kingai-browser/0.3.4/)，可执行 `python -m pip install kingai-browser`。

## 从完整示例开始

[Examples and prerequisites / 示例与前提](../examples/README.md) · [API recipes / 接口调用手册](../docs/API_EXAMPLES.md)

```powershell
# From repository root / 在仓库根目录，另开终端启动演示网页
python -m http.server 8765 --bind 127.0.0.1 --directory examples
# Then run in another terminal / 然后另开终端执行
python python/examples/browser_form_automation.py --live
```

完整流程展示环境列表、创建与设置、DOM 快照、元素查询、输入、点击、等待并核对结果。窗口需可见；生成的新环境在结束后保留。

## 调用结构与返回值

```python
from kingai_browser import KingAI

with KingAI() as api:
    profiles = api.profiles()  # Saved environment summaries / 环境摘要
    print(profiles)
    profile = api.create_profile("My unique environment", language="en-US")
    profile_id = profile["profileId"]
    api.update_profile(profile_id, name="My configured environment")
    browser = api.start(profile_id=profile_id)
    try:
        browser.new_tab("http://127.0.0.1:8765/demo.html")
        browser.wait(selector="#name", state="visible")
        print(browser.query(selector="#name", include_html=True))
        browser.fill("#name", "KingAI", humanize=False)
        print(browser.read())
    finally:
        browser.detach()  # Keep window / 保留窗口
```

`profileId` identifies saved environments; `sessionId` identifies a running session; `targetId` identifies a tab; `ref` identifies an observed element. / 四类 ID 分别代表环境、会话、标签和已观察元素，不可混用。

## 接口类别导航

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

## 生命周期、错误与权限

- Client close disconnects MCP; session close closes the browser. Detach keeps the browser available. / 客户端关闭、会话断开和浏览器关闭含义不同。
- Default start requires an existing unique 默认环境; it does not create one. / 默认启动不会自动创建缺失环境。
- Update only closed profiles; deletion requires explicit confirmation and removes persistent data. / 更新前关闭环境；删除需确认且会移除持久数据。
- Side effects are not automatically retried after timeout or observation failure. / 超时和观察失败不自动重放输入。
- Humanize needs valid entitlement; examples explicitly use false for basic form interaction. / 拟人化需要有效权益，演示显式关闭。
- PAGE_NOT_VISIBLE requires restoring the window and selecting the intended tab. / 页面不可见时恢复窗口并激活标签。
- Call sequences use one selected tab; serialize multi-step workflows. / 多步操作串行，不是 Playwright 多 Page 模型。

## 测试范围与许可

[SAMPLES.md](../SAMPLES.md) records earlier fixture tests. New examples, documentation and renames have not been built, checked or tested in this task. / 旧模拟测试不代表新增示例已实机验证；本轮未运行构建、检查或测试。

MIT: retain copyright/license and applicable third-party notices. / 允许传播、修改与商用，保留版权、许可及适用的第三方声明。
