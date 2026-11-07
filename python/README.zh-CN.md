# KingAI Python 使用说明

[English](README.md) | 简体中文 | [Project / 项目](../README.md)

**SDK 0.3.0 · MIT · Python 3.10+**

本库通过 stdio 调用已安装的 KingAI MCP，不需要 HTTP 服务或 Playwright。先安装浏览器并登录，MCP/Runtime 必须支持所需工具。

## 安装与定位

```powershell
python -m pip install --cache-dir D:/code/kingai-sdk-cache/pip ./python
```

```powershell
$env:KINGAI_MCP_EXECUTABLE = 'D:\Apps\KingAIBrowser\KingAIMcpServer.exe'
```

示例路径需替换。定位顺序为显式 SDK 参数、环境变量、管理器登记。不能把浏览器主程序当 MCP。依赖、临时文件、缓存与构建输出放 D 盘。公共包尚未发布。

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
