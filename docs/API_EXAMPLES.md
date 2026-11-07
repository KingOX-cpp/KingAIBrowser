# API examples / 接口调用手册

This is a recipe reference, not a script to run every operation on your account. Choose a section and substitute real IDs. / 本文按用途展示调用方法，不应把所有代码连续执行。环境、会话、元素 ID 必须来自真实返回值。

## 1. Calling conventions / 调用方式

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
