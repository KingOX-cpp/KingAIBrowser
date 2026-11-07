# API examples / 接口调用手册

Common SDK entry guide: [English](SDK_ENTRY_POINTS.md) / [中文](SDK_ENTRY_POINTS.zh-CN.md). The Python-specific section below is not a claim that all four languages expose BrowserAutomation; see the cross-language capability matrix first.

Four-language browser installer download and optional native-UI launch: [English](../INSTALLATION.md) / [中文](../INSTALLATION.zh-CN.md). This is explicit and separate from launch(), browser automation and MCP tool invocation. Downloads/installers have not been executed in this change.

This is a recipe reference, not a script to run every operation on your account. Choose a section and substitute real IDs. / 本文按用途展示调用方法，不应把所有代码连续执行。环境、会话、元素 ID 必须来自真实返回值。

## 1. Calling conventions / 调用方式

### Python entry points: launch, KingAI and BrowserAutomation

Detailed guide: [English](../python/ENTRY_POINTS.md) / [中文](../python/ENTRY_POINTS.zh-CN.md). Includes complete examples for all three entries, parameters, return values, DOM/state handling and lifecycle ownership.

| Entry | Purpose / 用途 | Typical caller / 使用者 |
| --- | --- | --- |
| `launch()` | Connect and open an environment in one entry; return a BrowserSession. / 简化连接和启动，返回浏览器会话。 | Ordinary Python automation scripts. / 普通自动化脚本。 |
| `KingAI` | Explicit client ownership, environment CRUD, tool discovery and session management. / 显式管理连接、环境与会话。 | Applications needing lifecycle/configuration control. / 需要管理环境和连接的应用。 |
| `BrowserAutomation` | Translate Agent action names into the same SDK operations and collect structured observations. / 接收 Agent action，执行后整理观察状态与错误。 | OpenManus BrowserUseTool and similar Agent adapters. / Agent 工具适配层。 |

These are layers of one SDK using the same installed MCP/Runtime. They do not provide three different browser engines. `BrowserAutomation` is implemented in `python/_kingai_automation.py` and exported from `kingai_browser`.

### BrowserAutomation: Agent action and state facade

It provides these interfaces:

- `execute(action, **arguments)`: dispatch an Agent action such as go_to_url, query, click_element, input_text, extract_content or mcp_call. Element actions require an observed ref or exact selector; the facade does not invent targets or plan tasks on its own.
- `get_current_state()`: read the current page, snapshot and tabs, returning an Agent-friendly dictionary including interactive_elements. This is a live observation call, not a cached browser database lookup.
- `describe_error(error)`: turn an error into structured information for the Agent adapter.
- `close()` / context exit: disconnect this facade's MCP connection while preserving the browser window. This differs from an explicit browser session close_browser().

中文：它的职责是“接收动作、调用 SDK、整理状态”，不是 AI 模型或自主规划器。页面变更动作会整理执行后的观察结果；观察失败不自动重放先前输入。输入是否派发与业务是否成功分开表示，Agent 必须根据页面结果判断。

```python
import json
from kingai_browser import BrowserAutomation

with BrowserAutomation(profile_id="actual-saved-profile-id") as agent_browser:
    # Replace the ID with one from KingAI.profiles(); do not invent one.
    result = agent_browser.execute("go_to_url", url="https://example.com")
    state = agent_browser.get_current_state()
    print(state["url"], state["title"])

    snapshot = json.loads(state["interactive_elements"])
    for element in snapshot.get("elements", []):
        print(element.get("ref"), element.get("name"))

    # Query through the facade rather than guessing an element index.
    links = agent_browser.execute("query", arguments={"selector": "a", "limit": 10})
    print(links)
```

Replace the saved ID before running; omit profile_id only to use the existing unique default environment. To resume an existing session, use `BrowserAutomation(session_id="actual-active-session-id")` with permission to attach; do not also set profile_id. If an ordinary script already has a BrowserSession, use its query/snapshot directly instead of opening another facade.

OpenManus keeps the tool name browser_use for compatibility, but its implementation delegates to `BrowserAutomation.execute()` and `get_current_state()`. The `interactive_elements` field is the SDK's serialization of a snapshot for that adapter, not a special browser-side storage field. / OpenManus 的 browser_use 是工具名称，BrowserAutomation 是工具内部调用的 Python SDK 类；两者不是同一个东西。

Lifecycle update: Python `with launch()` and Java automatic `Session.close()` detach owned connections and preserve browser windows. Non-owned context/resource exit performs no cleanup. Explicit shutdown is Python `close_browser()`/`close()`, Node `closeBrowser()`/`close()`, Java `closeBrowser()`, Go `CloseBrowser()`/`Close()`. The generic snippets below do not imply that every object named close has the same ownership semantics.

Java/Go input convenience methods now support options: `browser.click(ref, Map.of("humanize", false))`, `browser.fill(ref, text, Map.of("humanize", false))`, `browser.type(ref, text, options)`, `browser.hover(ref, options)`, `browser.waitFor(options)`; Go uses `Click(ctx,ref,Arguments{"humanize":false})`, `Fill(ctx,ref,text,options)`, `Type`, `Hover`, `Wait`. Existing ref-only calls remain valid. New code has not been executed in this change.

Python examples below assume `api` is a connected `KingAI` and `browser` is its running session. Session calls insert `session_id` automatically. Equivalent generic calls in every language:

```python
# Python: arbitrary installed tool; keyword arguments bind to the current session.
result = browser.call("browser_query", selector="#name", include_html=True)
```
```javascript
// Node.js: same tool and raw arguments; await every operation.
const result = await browser.call('browser_query', { selector: '#name', include_html: true });
```
```java
// Java: Session.call injects session_id, Jackson JsonNode is returned.
JsonNode result = browser.call("browser_query", Map.of("selector", "#name", "include_html", true));
```
```go
// Go: Session.Call injects session_id. Always propagate the returned error.
result, err := browser.Call(ctx, "browser_query", kingai.Arguments{"selector": "#name", "include_html": true})
if err != nil { return err }
```

The same translation applies to every session-tool recipe below: tool name and JSON fields stay unchanged. Client-level tools use `api.call(name, args)`, `await api.call(name,args)`, `api.call(name,map)` or `api.Call(ctx,name,args)` respectively. / 后续每个工具都可按上述四种写法调用；原始字段不自动转换为 camelCase。

## 2. Environment list and configuration / 环境列表与设置

Runnable Python source: [profile_management.py](../python/examples/profile_management.py).

```python
saved = api.profiles()                        # profiles_list: saved summaries
created = api.create_profile("Unique example", language="en-US")
profile_id = created["profileId"]             # ID returned by creation
summary = api.profile(profile_id)             # profiles_get
api.update_profile(profile_id, name="Configured example", patch={
    "locale": {"language": "en-US", "accept_languages": "en-US,en"}
})
updated = api.profile(profile_id)
# Optional, destructive: only after explicitly closing this environment.
# api.delete_profile(profile_id, confirm=True)
```

Create/update do not open a browser. Update refuses running environments. Names must be unique; a group_name, if supplied, must identify an existing group. `patch` merges objects recursively; arrays replace. Do not pass secrets to logging. / 创建和配置不等于启动；更新前需关闭环境。不要用示例自动删除用户原有环境。

Equivalent raw tools: `profiles_list {}`, `profiles_get {profile_id}`, `profiles_create {name,language}`, `profiles_update {profile_id,name,patch}`, `profiles_delete {profile_id,confirm:true}`.

## 3. Session ownership / 会话生命周期

```python
browser = api.start(profile_id=profile_id, headless=False)
session_id = browser.session_id
active = api.sessions()                       # inspect real active sessions
# Another client can request attach only if server ownership rules allow it:
# browser = api.attach(session_id)
browser.detach()                             # leave browser available
# browser.close()                            # explicitly close the browser
# api.close()                                # only close this client's MCP
```

Default `api.start()` finds the existing unique 默认环境. Explicit `temporary=True` is a separate opt-in mode. It is never a silent fallback. / 默认环境缺失会报错；临时环境须明确请求。异常断线后先查看状态，不要无条件重新启动。

## 4. Tabs and navigation / 标签页与导航

```python
opened = browser.new_tab("http://127.0.0.1:8765/demo.html")
target_id = opened["targetId"]
all_tabs = browser.tabs()
browser.activate_tab(target_id)
browser.goto("http://127.0.0.1:8765/demo.html")
# Explicitly close ONLY a tab you created and no longer need:
# browser.close_tab(target_id)
```

Operations act on the selected tab. Do not concurrently change tabs during input or a multi-step workflow. / 会话不是多 Page 模型，标签切换与输入请串行。

## 5. Page text, snapshot, DOM query and pagination / 页面观察

### Open a page and obtain DOM elements / 打开页面后获取 DOM 元素

For ordinary Python automation, use the session's `query()` and `snapshot()` methods directly. You do not need `interactive_elements` or an Agent framework. / 普通 Python 程序不需要先创建 browser_state，也不需要 Agent；打开网站后直接调用 query、snapshot。

```python
from kingai_browser import launch

with launch() as browser:
    browser.new_tab("https://example.com")
    browser.wait(selector="body", state="visible", timeout_ms=15000)

    # Read a compact DOM/accessibility observation with actionable refs.
    snapshot = browser.snapshot(mode="interactive", limit=30)
    print(snapshot.get("text", ""))

    # Query actual DOM elements and request bounded outerHTML when needed.
    result = browser.query(selector="a", include_html=True, limit=20)
    for element in result.get("elements", []):
        print(element.get("ref"), element.get("tag"), element.get("name"))
        print(element.get("attributes", {}))

    # On a page containing your own form, query the exact intended input:
    # found = browser.query(selector="#name", limit=2)["elements"]
    # if len(found) != 1:
    #     raise RuntimeError("Expected exactly one input")
    # browser.fill(ref=found[0]["ref"], text="KingAI", humanize=False)
```

The executable portion reads links from example.com without clicking or submitting anything. The commented input recipe requires a page containing #name; example.com has no such input. Context exit preserves the window. / 上面的实际执行部分只读取页面中的链接；注释中的输入示例要用于确实存在该输入框的页面。

`query()` without filters enumerates bounded DOM summaries, not only accessibility interaction candidates. `snapshot(mode="interactive")` focuses on interaction candidates; the default compact snapshot can also contain contextual text and structure. These are JSON observations, **not live JavaScript DOM objects or a complete unbounded HTML document**. Element fields can include ref, tag, role, name, attributes, text, bounds, states and frameId, depending on the installed server and observation mode. / 返回的是 DOM 观察摘要，不是可直接调用 element.click() 的 DOM 对象；动作应交给 SDK 的 click/fill 等接口。

### What interactive_elements contains / interactive_elements 的来源和内容

`interactive_elements` belongs to the optional `BrowserAutomation` Agent facade. It is created in Python by `capture_state()` in `python/_kingai_automation.py`, not saved in the browser or profile database. The implementation performs:

```python
snapshot = browser.snapshot(max_chars=20000)
state = {"interactive_elements": json.dumps(snapshot, ensure_ascii=False)}
```

This abbreviated fragment explains the field assignment; the real state also contains url, title, session_id, tabs, page_content and help. The field is a **JSON string containing the entire bounded snapshot response**, not an element list. Its historical name does not mean it contains only interactive elements: the facade currently requests the default compact snapshot.

中文：这个字段是 SDK 为 Agent 整理状态时写入的。字符串解析后才是快照字典，其中 `elements` 才是元素数组；不要把整个字段当数组遍历，也不要以为它是浏览器持久保存的全页 DOM。

```python
import json
from kingai_browser import BrowserAutomation

with BrowserAutomation() as agent_browser:
    agent_browser.execute("go_to_url", url="https://example.com")
    browser_state = agent_browser.get_current_state()
    snapshot = json.loads(browser_state["interactive_elements"])
    for element in snapshot.get("elements", []):
        print(element.get("ref"), element.get("tag"), element.get("name"))
    print(snapshot.get("text", ""))
    print("Snapshot truncated:", snapshot.get("truncated", False))
```

The OpenManus adapter consumes this facade state. If you already opened a page using `launch()`/`KingAI`, continue with that same session's `query()`/`snapshot()`; do not instantiate a second facade merely to get this field. To observe through a new facade, explicitly attach an authorized existing session ID instead of starting another environment. / 已经打开网站的普通脚本应复用原会话，不要为了获取该字段重复启动默认环境。

### Snapshot budget and pagination / 快照预算与分页

```python
page = browser.read()                         # readable page content
snapshot = browser.snapshot(mode="interactive", limit=30, max_chars=12000)
query = browser.query(selector="input, textarea, button", include_html=True, limit=20)
elements = query["elements"]                 # bounded DOM summaries, not live DOM objects
for element in elements:
    print(element.get("ref"), element.get("tag"), element.get("name"))
# Follow the SAME captured observation without resending filters:
if query.get("nextCursor"):
    next_page = browser.query(cursor=query["nextCursor"])
```

You may filter by selector, role, name or text. `include_html` is bounded outerHTML, not an unlimited page dump. Refs are opaque and session/document-bound. Query again after navigation or DOM replacement. / 不要猜测 ref，不要把旧页面的 ref 存成长期选择器；分页只传服务器返回的 cursor。

## 6. Wait, fill, append, click, keyboard, hover and scroll / 输入交互

```python
browser.wait(selector="#name", state="visible", timeout_ms=15000)
found = browser.query(selector="#name", limit=2)
if len(found["elements"]) != 1:
    raise RuntimeError("Expected exactly one name input")
name_ref = found["elements"][0]["ref"]
browser.fill(ref=name_ref, text="KingAI", humanize=False)     # replace existing text
browser.type(ref=name_ref, text=" SDK", humanize=False)      # append text
browser.key("Tab", humanize=False)
browser.hover("#submit", humanize=False)
browser.scroll(300, humanize=False)
browser.click("#submit", humanize=False)
browser.wait(selector='#result[data-submitted="true"]', timeout_ms=10000)
result_text = browser.evaluate("document.querySelector('#result').textContent")
```

`selector` and `ref` are alternatives, not two identifiers to supply together. `humanize=False` is explicit for basic examples; enabling it requires valid entitlement. An action result is not a business-success assertion. / 示例关闭拟人化不绕过其他授权；点击派发后仍应核对页面结果。

## 7. JavaScript and bounded previews / 求值与预览

```python
title = browser.evaluate("document.title")
preview = browser.evaluate_preview("({title:document.title,text:document.body.innerText})")
if preview.get("truncated"):
    print("Preview is partial; request selected fields or read-only pages of data")
```

Java/Node use `evaluatePreview`; Go uses `EvaluatePreview`. Large `evaluate` results can produce RESULT_TOO_LARGE after execution already occurred. Never rerun a side-effect expression merely to retrieve output. / 预览不是完整结果；副作用不能因结果过大而自动重跑。

## 8. Screenshot, PDF and file transfer / 截图与文件

```python
# Configure absolute trusted paths when constructing the client:
# KingAI(file_roots=[r"D:\demo\uploads"],
#        download_dir=r"D:\demo\downloads", artifact_dir=r"D:\demo\artifacts")
image = browser.screenshot()
document = browser.pdf()
# Target-page examples; the local form does not contain these elements:
# browser.upload([r"D:\demo\uploads\document.txt"], selector='input[type="file"]')
# browser.download(selector="#download-link")
```

Artifact responses describe server-produced files; inspect actual returned fields instead of assuming a local byte array. Upload paths must be within permitted roots. Download and upload examples require a page containing those targets. / 文件示例需换成实际上传控件或下载链接，不会假定演示表单具有这些功能。

## 9. Cookies and Storage / 站点状态

```python
cookies = browser.cookies()
storage = browser.storage()
# Do not print/export cookies or storage into public logs.
```

Read schemas for other state-changing tools using the installed catalog. Do not invent setter parameters. / 修改 Cookie、Storage 等扩展操作先查看安装版 schema，不猜参数。

## 10. Skills / 已保存工作流

```python
skills = api.skills()
# Use a real skill_id from the list, then inspect required parameters:
# description = api.describe_skill(skill_id)
# started = api.run_skill(profile_id, skill_id, **options_from_description)
# status = api.skill_status(started["runId"])
# api.cancel_skill(started["runId"])  # only if you intend to cancel
runs = api.skill_runs()
```

Skill parameter names depend on the saved skill and installed schema. This intentionally does not fabricate a runnable skill ID. Go/Java can access tools without convenience methods through `Call` / `call`. / 不伪造 Skill ID 和参数；先查询、再按实际定义运行。

## 11. Every installed tool / 全部安装版接口

```powershell
python python/examples/mcp_tool_catalog.py
python python/examples/mcp_tool_catalog.py --tool browser_query
```

The catalog includes installed iframe, network, console and other tools beyond convenience methods. Before a raw call, read required fields and descriptions. It is intentionally read-only. / 工具目录覆盖实际服务端全部 schema，并不意味着应自动执行所有接口。

## 12. Failure handling / 错误处理

```python
from kingai_browser import KingAIError
try:
    page = browser.read()
except KingAIError as error:
    print(error.code)  # keep structured details private unless sanitized
    raise             # no automatic replay of a previous click/type
```

Inspect real Runtime request IDs with `request_status` only when the backend provides one; JSON-RPC IDs are not substitutes. PAGE_NOT_VISIBLE requires restoring/activating the target page. Cross-client ownership and account limits remain enforced by Runtime. / 不用重试掩盖未知执行结果，也不绕过环境 Lease。

These recipes were authored from the SDK source and tool contracts, not executed during this documentation task. / 本轮未运行构建、检查、测试或实机示例。
