# 四语言 SDK 调用入口：区别与选择

[English](SDK_ENTRY_POINTS.md) | 简体中文

这是一份公共入口说明，不局限于 Python。所有入口共用安装版 MCP、Runtime 和浏览器；它们是同一个 SDK 体系的不同封装层，不是不同内核。同一任务通常选一个层级，不要重复启动同一环境。

## 1. 当前四种语言分别实现了什么

| 层级 | Python | Node.js / TypeScript | Java | Go |
| --- | --- | --- | --- | --- |
| 快速启动入口 | launch() | await launch() | KingAI.launch() | kingai.Launch(ctx, options, profileID) |
| 显式客户端 | KingAI | KingAI | KingAI | Connect 返回的 Client |
| 浏览器会话对象 | BrowserSession | BrowserSession | KingAI.Session | Session |
| Agent 动作/状态封装 | BrowserAutomation | BrowserAutomation | 暂无该封装类 | 暂无该封装类型 |

**目前 Python、Node 有三层入口，Java、Go 有两层。** Java/Go 能通过通用调用访问全部已安装 MCP 工具，但这不等于已经有 execute/get-current-state 形式的 Agent facade。不要根据文档猜测并导入不存在的 Java/Go BrowserAutomation。

## 2. 快速入口：直接操作网页

适合普通导航、读取、DOM 查询、点击输入脚本。它内部创建客户端并启动环境，返回会话对象，不要求业务代码先管理客户端连接。

| 语言 | 默认环境 | 指定保存环境 |
| --- | --- | --- |
| Python | launch() | launch(profile_id=id) |
| Node | await launch() | await launch({profileId:id}) |
| Java | KingAI.launch() | KingAI.launch(options,id) |
| Go | kingai.Launch(ctx, options, "") | kingai.Launch(ctx, options,id) |

默认环境必须已存在且唯一；缺失会报错，不会自动创建临时环境。先安装、登录，再调用入口；launch 不自动下载安装。

Python：

```python
from kingai_browser import launch
with launch() as browser:
    browser.new_tab("https://example.com")
    print(browser.query(selector="a", limit=20))
```

Node.js：

```javascript
import { launch } from '@kingai/browser-api';
const browser = await launch();
try {
  await browser.newTab('https://example.com');
  console.log(await browser.query({ selector: 'a', limit: 20 }));
} finally { await browser.detach(); }
```

Java：放在应用方法中，导入 KingAI 和 Map：

```java
try (KingAI.Session browser = KingAI.launch()) {
    browser.newTab("https://example.com");
    System.out.println(browser.query(Map.of("selector", "a", "limit", 20)));
}
```

Go：放在返回 error 的函数中，使用已有 ctx，导入 kingai 和 fmt：

```go
browser, err := kingai.Launch(ctx, kingai.Options{}, "")
if err != nil { return err }
defer browser.Detach(ctx)
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
elements, err := browser.Query(ctx, kingai.Arguments{"selector": "a", "limit": 20})
if err != nil { return err }
fmt.Println(elements)
return nil
```

以上实际操作只读取链接，不点击、不提交。会话拥有入口内部创建的客户端。Python 上下文退出、Java 自动资源退出，以及 Node/Go 显式 detach 都保留窗口并释放 owned 连接。

## 3. 显式客户端：管理环境、会话与连接

需要获取环境列表、创建/配置环境、发现/接入已有会话、管理多个窗口时使用客户端。四种语言都有这一层：Python/Node/Java 名为 KingAI，Go 由 Connect 返回 Client。

| 操作 | Python | Node | Java | Go |
| --- | --- | --- | --- | --- |
| 环境列表 | profiles() | profiles() | profiles() | Profiles(ctx) |
| 创建环境 | create_profile(name) | createProfile(name) | createProfile(name) | CreateProfile(ctx,name,nil) |
| 启动指定环境 | start(profile_id=id) | start({profile_id:id}) | start(Map.of("profile_id",id)) | Start(ctx,Arguments{"profile_id":id}) |
| 查询/恢复会话 | sessions / attach | sessions / attach | sessions / attach | Sessions / Attach |
| 工具发现/通用调用 | tools / call | tools / call | tools / call | Tools / Call |
| 客户端释放 | api.close() | await api.close() | api.close() | api.Close() |

Node 方法需要 await；Java/Go 的请求参数和错误处理见各语言 README。客户端 close 只释放 MCP，不是显式关闭浏览器。客户端 start 返回的会话不拥有外部客户端，调用方需自己关闭客户端。创建环境不等于启动，修改前应关闭环境；删除会移除数据，必须显式确认。

完整分类参数与四语言通用调用示例见 [API_EXAMPLES.md](API_EXAMPLES.md)。

## 4. Agent facade：给 Agent 适配层使用

目前只有 Python 和 Node 实现 BrowserAutomation。它没有大模型，也不自主规划任务；它接收 go_to_url、click_element、input_text 等 action，执行同一 SDK 操作，再整理观察状态与错误，适合 OpenManus 这类框架。

Python：

```python
import json
from kingai_browser import BrowserAutomation
with BrowserAutomation() as agent:
    agent.execute("go_to_url", url="https://example.com")
    state = agent.get_current_state()
    snapshot = json.loads(state["interactive_elements"])
    print(snapshot.get("elements", []))
```

Node：

```javascript
import { BrowserAutomation } from '@kingai/browser-api';
const agent = new BrowserAutomation();
try {
  await agent.execute('go_to_url', { url: 'https://example.com' });
  const state = await agent.getCurrentState();
  console.log(JSON.parse(state.interactive_elements).elements);
} finally { await agent.close(); }
```

interactive_elements 是有预算限制的快照 JSON 字符串，解析后 elements 才是元素数组，不是浏览器持久化字段或活的 DOM 对象。普通脚本直接调用会话 query/snapshot，无需绕到这个字段。

Java/Go 如需接 Agent，可基于会话 read/query/snapshot 与通用调用编写适配层，但当前库尚未提供同名 facade。支持 stdio MCP 的 Agent 还可不经过 SDK，直接接入安装版 MCP，见[配置模板](../examples/integrations/README.md)。

## 5. 生命周期与关闭方法

| 情况 | 行为 |
| --- | --- |
| Python with launch() 退出 | detach 并释放 owned 客户端，保留窗口 |
| Java Session 自动资源 close() | owned 会话 detach 并释放客户端，保留窗口；非 owned 自动退出不清理外部连接 |
| Node/Go launch 会话 detach/Detach | detach 并释放 owned 客户端，保留窗口 |
| Python/Node BrowserAutomation.close | 释放 facade 客户端，保留窗口 |
| 显式关闭浏览器 | Python close_browser()/close()；Node closeBrowser()/close()；Java closeBrowser()；Go CloseBrowser()/Close() |

释放连接后，原对象不能继续操作保留窗口。可用 Manager 关闭，或由新客户端发现真实会话并在授权允许时 attach。Java 在客户端已关闭后调用 closeBrowser 会明确报 SESSION_DISCONNECTED。不要因为各语言都有 close 就推断语义一样。

三种层级都不绕过登录、会员、并发、Lease、页面可见性与会话归属限制。观察到输入派发不等于业务完成；异常后不自动重放副作用。

本轮只补文档，未执行示例或运行构建、检查、测试。[Python 进一步说明](../python/ENTRY_POINTS.zh-CN.md) · [故障排查](../TROUBLESHOOTING.md)。
