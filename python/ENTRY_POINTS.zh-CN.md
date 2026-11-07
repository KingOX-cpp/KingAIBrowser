# Python 三种调用入口：区别与用法

本文是 Python 专项详细说明。四语言公共架构、能力差异及 Java/Go/Node 用法请先看[四语言入口总览](../docs/SDK_ENTRY_POINTS.zh-CN.md)。

[English](ENTRY_POINTS.md) | 简体中文 | [Python 使用说明](README.zh-CN.md) | [接口示例手册](../docs/API_EXAMPLES.md)

## 1. 先选适合自己的入口

三种入口共用同一个已安装的 MCP、Runtime 和浏览器执行层，不是三个浏览器，也不需要在一个任务中各创建一遍。

| 入口 | 你拿到的对象 | 主要用途 | 推荐场景 |
| --- | --- | --- | --- |
| `launch()` | `BrowserSession` 会话 | 简化连接和启动，直接操作网页 | 写一个打开网页、查询 DOM、点击输入的脚本 |
| `KingAI` | 客户端；`start()` 再返回会话 | 环境 CRUD、工具发现、启动与接入会话、管理连接 | 环境管理程序、多环境自动化、需要自己掌握生命周期的应用 |
| `BrowserAutomation` | Agent 动作与状态封装 | 将 action 转为 SDK 操作，并整理操作后观察、错误与状态 | OpenManus 的 BrowserUseTool 等 Agent 适配层 |

**普通脚本先用 launch；需要环境管理用 KingAI；接 Agent action 接口用 BrowserAutomation。** BrowserAutomation 自身不带大模型，不会理解目标并自主规划，也不让浏览器获得额外权限。

## 2. 共同前提

```powershell
python -m pip install kingai-browser==0.3.0
python -m kingai_browser doctor
```

浏览器需安装、登录且 MCP/Runtime 配套。SDK 通过显式 `mcp_executable`、`KINGAI_MCP_EXECUTABLE` 或 Manager 安装登记定位 MCP，不因为调用 launch 就自动下载安装浏览器。显式下载入口是 `install()`，见[安装说明](../INSTALLATION.zh-CN.md)。

省略环境 ID 时，打开已有且唯一的“默认环境”；缺失会报错，不自动创建或回退为临时环境。已经运行的环境可能返回 SESSION_EXISTS，应先发现会话并在授权允许时 attach，不盲目重复启动。

## 3. launch：直接拿到一个浏览器会话

```python
from kingai_browser import launch

with launch() as browser:
    browser.new_tab("https://example.com")
    browser.wait(selector="body", state="visible", timeout_ms=15000)
    links = browser.query(selector="a", include_html=True, limit=20)
    for element in links.get("elements", []):
        print(element.get("ref"), element.get("name"))
    print(browser.read())
```

它内部创建 KingAI 客户端并调用 start，返回 BrowserSession。会话提供 `new_tab`、`query`、`snapshot`、`click`、`fill`、`read` 等方法。这里示例只读取链接，没有点击或提交。

指定环境与连接选项：

```python
browser = launch(
    profile_id="actual-saved-profile-id",
    headless=False,
    timeout=60,
)
try:
    browser.new_tab("https://example.com")
    print(browser.snapshot(mode="interactive", limit=30))
finally:
    browser.detach()
```

先把 ID 替换成环境列表中的真实值。`timeout` 是客户端请求超时秒数；不是任务总时长。需要临时环境时必须明确传 `temporary=True`，不要同时用保存环境 ID 表达另一种身份。

`with launch()` 退出时 detach、释放它拥有的 MCP 连接，保留浏览器窗口。若明确要关闭窗口，可在退出前调用 `browser.close_browser()`；`browser.close()` 是同义方法。退出后不能继续用原会话操作窗口。

## 4. KingAI：显式管理环境和会话

```python
from uuid import uuid4
from kingai_browser import KingAI

with KingAI() as api:
    print(api.profiles())
    created = api.create_profile("Example " + uuid4().hex[:12], language="en-US")
    profile_id = created["profileId"]
    api.update_profile(profile_id, name="Configured " + uuid4().hex[:12])
    print(api.profile(profile_id))

    browser = api.start(profile_id=profile_id)
    try:
        browser.new_tab("https://example.com")
        print(browser.query(selector="a", limit=20))
    finally:
        browser.detach()
```

这里创建了一套真实持久环境，结束后不删除，重复运行会留下多套环境。修改配置必须在环境关闭时进行；删除持久数据必须显式确认，不应当作通用 finally 清理。

KingAI 客户端的常用能力：

- `profiles()`、`profile(id)`：列表与单个环境摘要。
- `create_profile`、`update_profile`、`delete_profile`：保存环境管理。
- `start`、`sessions`、`attach`：启动、发现和显式接入会话。
- `tools()`、`call(name, arguments)`：发现并调用安装版工具。
- `close()`：只断开该客户端的 MCP，不等于关闭它曾经打开的浏览器。

同一个客户端可以管理多套会话；同会话的标签切换与输入应串行。由 `api.start()` 返回的会话不拥有外部客户端，所以 `browser.detach()` 后仍由你通过外层 `with KingAI()` 管理客户端。它与 launch 返回的 owned 会话有不同的连接归属。

已有会话恢复应使用真实 session ID：

```python
with KingAI() as api:
    print(api.sessions())
    # Select an actual authorized session ID from the response.
    # browser = api.attach("actual-active-session-id")
    # print(browser.snapshot())
    # browser.detach()
```

保存环境的 `profileId`、运行会话的 `sessionId`、标签的 `targetId`、元素的 `ref` 不能互换。

## 5. BrowserAutomation：给 Agent 使用的动作/观察接口

```python
import json
from kingai_browser import BrowserAutomation

with BrowserAutomation() as agent_browser:
    operation = agent_browser.execute("go_to_url", url="https://example.com")
    state = agent_browser.get_current_state()
    print(state["url"], state["title"])

    snapshot = json.loads(state["interactive_elements"])
    for element in snapshot.get("elements", []):
        print(element.get("ref"), element.get("name"))

    links = agent_browser.execute("query", arguments={"selector": "a", "limit": 20})
    print(links)
```

首次执行需要页面的 action 时，它才启动或 attach 浏览器；刚创建对象后不能直接 get_current_state，需先 go_to_url/open_tab 等。构造参数支持 `profile_id` 或 `session_id` 二选一，以及 `headless` 和底层 SDK 连接选项。

| 方法 | 职责 |
| --- | --- |
| `execute(action, **arguments)` | 执行 go_to_url、click_element、input_text、query 等 action；调用方仍负责选择目标和规划任务 |
| `get_current_state()` | 重新读取 page、snapshot、tabs 并组装状态字典，不是读取持久化网页缓存 |
| `describe_error(error)` | 提供结构化错误与处理提示；部分连接不确定错误会阻止后续常规操作，避免重复副作用 |
| `close()` / 上下文退出 | 释放它自己的 MCP 连接，保留窗口；不要把它当作 BrowserSession.close() |

`interactive_elements` 是 SDK 写入状态字典的 **JSON 字符串**，包含整个有预算限制的 snapshot 响应；`json.loads` 后其中的 `elements` 才是元素数组。它不是浏览器数据库字段，不是活的 DOM 对象，也不保证是全量页面。当前封装请求默认 compact 快照，因此历史命名不表示“只有可交互元素”。

操作回执中的 `operationResult` 记录执行返回；页面变更动作还会整理 `observation`、`observationStatus` 和 `businessOutcome=not_verified`。观察失败不自动重复点击。Agent 仍需独立判断页面结果；不能把 actionDispatched 当作业务完成。

## 6. 获取 DOM 和输入，应选择哪个接口？

普通脚本使用 `browser.query()` / `browser.snapshot()`，不必通过 interactive_elements。Agent 适配层需要统一状态时才使用 BrowserAutomation.get_current_state()。

```python
# On a page that actually contains this form input:
found = browser.query(selector="#name", limit=2)["elements"]
if len(found) != 1:
    raise RuntimeError("Expected one input")
browser.fill(ref=found[0]["ref"], text="KingAI", humanize=False)
```

该片段需要一个当前存活的会话和真正含 #name 的表单页，example.com 没有该输入框。完整本地表单见[示例导航](../examples/README.md)。观察返回的是 DOM 摘要；动作使用 SDK，不对摘要调用 element.click()。

## 7. 生命周期速查

| 对象与操作 | 连接 | 浏览器窗口 |
| --- | --- | --- |
| 退出 `with launch()` | 释放其 owned 客户端 | 保留 |
| launch 会话 `detach()` | detach 并释放 owned 客户端 | 保留 |
| launch 会话 `close_browser()` / `close()` | 显式关闭后释放 owned 客户端 | 关闭 |
| 退出 `with KingAI()` / `api.close()` | 释放该客户端 | 不显式关闭窗口 |
| `api.start()` 会话的 `detach()` | 释放会话控制，不自动关闭外部客户端 | 保留 |
| 非 owned session 的 `with browser` 退出 | 不接管连接，不做自动清理 | 保留 |
| 退出 `with BrowserAutomation()` / facade.close() | 释放 facade 的客户端 | 保留 |

释放连接后的原对象不可继续操作。需要关闭保留窗口时，用 Manager，或用新客户端发现真实会话并在授权允许时 attach。不要自动重连、强行接管 SESSION_BUSY，或在不确定结果后重放提交。

三种入口不改变账号并发、Lease、humanize 权益或页面可见性要求，也不会开放 raw CDP。AsyncKingAI 是显式客户端的异步接口；它不是另一个浏览器内核，详见 Python 使用说明。

本次仅补充文档，未运行示例、构建、检查或测试。浏览器行为与安装版能力仍需实机验证。
