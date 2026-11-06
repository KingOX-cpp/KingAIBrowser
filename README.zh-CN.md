<div align="center">
  <img src="images/new-logo.png" width="80" alt="KingAI Browser" />
  <h1>KingAI Browser</h1>
  <p><strong>独立指纹环境，让 AI Agent 真正操控浏览器。</strong></p>
  <p>Python · Node.js / TypeScript · Java · Go · Agent MCP</p>
  <p>简体中文 | <a href="README.md">English</a> | <a href="https://www.kingaibrowser.cn/">官方网站</a> | <a href="https://kingaibrowser.ccwu.cc/">备用网站</a> | <a href="https://www.kingaibrowser.cn/help/zh/">使用帮助</a></p>
</div>

KingAI Browser 将**持久化指纹环境、Chromium/Blink 源码级修改、浏览器原生自动化**结合起来。AI Agent 通过 **stdio MCP** 操作浏览器，开发者通过 **Python、Node.js、Java、Go SDK** 编写自动化程序，两种方式共用安装版 MCP、Runtime 和浏览器执行内核。

**SDK 0.3.0 · BSD-3-Clause 开源 · 无需 Playwright · 无需 HTTP 服务**

本仓库开源客户端 SDK、调用示例和测试。请从[官方网站](https://www.kingaibrowser.cn/)或[备用网站](https://kingaibrowser.ccwu.cc/)下载浏览器。浏览器内核补丁、Manager、MCP/Runtime 可执行程序由浏览器安装版另行提供，不包含在本仓库的 SDK 开源许可中。目前尚未发布 PyPI、npm、Maven 公共包，请按下文从源码安装。

![KingAI 指纹环境管理器](images/manager-dashboard.png)

## 指纹环境与 AI 自动化

| 能力 | 技术与用途 |
| --- | --- |
| 持久化指纹环境 | 每个 UUID 环境独立保存浏览器数据、Cookie、缓存、代理配置和指纹噪声 Key，支持跨会话复用同一身份。 |
| Chromium / Blink 源码级修改 | 在浏览器引擎层处理 UA / Client Hints、Canvas、Audio、ClientRects、字体、WebRTC、WebGL / WebGPU 和硬件相关指纹面。 |
| 跨指纹面一致性 | 协调语言、时区、代理地区、硬件和图形配置，并在启动前校验冲突。 |
| 浏览器原生 humanize | 鼠标轨迹、键盘节奏、滚动在浏览器输入层实现，同时处理鼠标按键与压力信号；实际使用需要有效会员权益。 |
| 面向 Agent 的 MCP | 打开保存环境、读取页面、定位元素、点击、输入、导航、管理标签页，以结构化结果供 Agent 决策。 |
| 可复用 Skill | 在浏览器中录制工作流；Agent 通过 MCP 发现参数、启动回放、查询进度和取消任务。 |
| 四种语言 SDK | Python、Node.js/TypeScript、Java、Go 调用同一套 MCP 工具，便于接入自己的 Agent 或业务程序。 |

浏览器还提供多窗口同步、Skill 单步调试等能力。指纹管理器的日常环境管理与启动免费；humanize、自动化并发等权益以当前安装版和账号配置为准。SDK 不改变原有权限与额度规则。详见[浏览器技术介绍](BROWSER_TECHNOLOGY.md)。

## CDP 检测与自动化信号防护

KingAI 的自动化信号防护落在 **Chromium/Blink 源码层和浏览器输入层**，包括 `navigator.webdriver`、自动化鼠标事件的 buttons / pressure 等。Agent 经由受控 MCP 工具操作浏览器，**无需获取 DevTools 端口、调试 WebSocket URL，也无需 Playwright/Puppeteer 连接**。

SDK 不开放无限制 raw CDP。浏览器内部仍可能使用受保护的 Chromium 接口；stdio 传输本身并不能消除自动化信号。上述设计用于减少可识别的自动化差异，**不代表所有网站都无法检测或一定放行**；代理 IP、账号历史、行为和网站规则也会影响结果。

## 调用架构

```text
AI Agent ─────────────────────────┐
                                  ▼
Python / Node.js / Java / Go → 安装版 KingAI MCP（stdio）
                                  │ 认证 IPC
                                  ▼
                              KingAI Runtime
                                  │
                                  ▼
                         KingAI 浏览器 + 指纹环境
```

SDK 管理自己的 MCP 子进程连接，不需要额外部署 HTTP 常驻服务。Runtime 负责浏览器执行和账号/环境访问，SDK 不自行拼装或导出完整指纹配置。

## 使用前准备

1. 安装 KingAI Browser，通过管理器登录。MCP 与 Runtime 须配套，且支持 SDK 0.3.0 所需工具；仅更新 SDK 不会升级浏览器服务。
2. 找到 **KingAIMcpServer.exe**，旁边应有 **KingAIRuntime.exe**。浏览器主程序不是 MCP Server。
3. 设置路径，或使用兼容管理器写入的当前用户安装登记；管理器不需要仅为路径发现一直开着。

```powershell
# 将示例替换为自己安装目录里的 MCP 程序。
$env:KINGAI_MCP_EXECUTABLE = 'D:\Apps\KingAIBrowser\KingAIMcpServer.exe'
git clone https://github.com/KingOX-cpp/KingAIBrowser.git D:\code\KingAIBrowser
cd D:\code\KingAIBrowser
```

定位优先级：SDK 显式参数 → `KINGAI_MCP_EXECUTABLE` → 管理器安装登记。SDK 不扫描磁盘、不自动下载浏览器。目前示例测试脚本面向 Windows；源码中的其他平台路径不代表对应浏览器发行版已经验证。

## Python

要求 Python 3.10+，运行时仅使用 Python 标准库。

```powershell
New-Item -ItemType Directory -Force D:\code\kingai-sdk-temp | Out-Null
$env:TEMP = 'D:\code\kingai-sdk-temp'
$env:TMP = $env:TEMP
python -m pip install --cache-dir D:\code\kingai-sdk-cache\pip .\python
python .\examples\sync.py --live
```

```python
from kingai_browser import KingAI

with KingAI() as api:
    print(api.profiles())                    # 获取保存环境
    profile = api.create_profile("Python 演示环境")
    browser = api.start(profile_id=profile["profileId"])
    browser.new_tab("https://example.com")
    print(browser.read())
    browser.detach()                        # 结束会话，保留浏览器
```

同时提供 `AsyncKingAI` 异步入口与 `BrowserAutomation` Agent 封装。[Python 说明](python/README.md) · [同步 sample](examples/sync.py) · [异步 sample](examples/async.py)。

## Node.js / TypeScript

要求 Node.js 22+。在自己的调用项目中安装本地源码包：

```powershell
npm install --cache D:\code\kingai-sdk-cache\npm D:\code\KingAIBrowser
```

```javascript
import { KingAI } from '@kingai/browser-api';

const api = new KingAI();
try {
  console.log(await api.profiles());
  const profile = await api.createProfile('Node 演示环境');
  const browser = await api.start({ profile_id: profile.profileId });
  await browser.newTab('https://example.com');
  console.log(await browser.read());
  await browser.detach();
} finally { await api.close(); }
```

提供 TypeScript 类型声明。运行[仓库 sample](examples/node.mjs)前，在仓库目录执行 `npm install --cache D:\code\kingai-sdk-cache\npm`，然后执行 `node examples/node.mjs --live`。

## Java

要求 Java 17+ 和 Maven，使用 Jackson 编解码，直接通过 stdio 连接 MCP。

```powershell
mvn -f java/pom.xml -Dmaven.repo.local=D:/code/kingai-sdk-cache/m2 -Dkingai.build.directory=D:/code/kingai-sdk-build/java install
```

调用项目使用相同本地 Maven 仓库，并添加依赖 `cn.kingaibrowser.sdk:kingai-browser:0.3.0`。该坐标目前仅供本地安装，尚未发布 Maven Central。

```java
import cn.kingaibrowser.sdk.KingAI;

try (KingAI api = new KingAI()) {
    System.out.println(api.profiles());
    KingAI.Session browser = api.start(); // 已保存的唯一“默认环境”
    browser.newTab("https://example.com");
    System.out.println(browser.read());
    browser.detach();
}
```

[Java 说明](java/README.md) · [包含创建环境的完整 sample](java/src/main/java/cn/kingaibrowser/sdk/samples/Sample.java)。

## Go

要求 Go 1.24+。调用项目的 `go.mod` 可引用本地仓库：

```go
require github.com/KingOX-cpp/KingAIBrowser/go v0.0.0
replace github.com/KingOX-cpp/KingAIBrowser/go => D:/code/KingAIBrowser/go
```

这里的 `v0.0.0` 仅用于本地 replace，并非已发布版本标签。导入 `kingai "github.com/KingOX-cpp/KingAIBrowser/go"` 后，在自己的函数中调用：

```go
api, err := kingai.Connect(ctx, kingai.Options{})
if err != nil { return err }
defer api.Close()
browser, err := api.Start(ctx, nil) // 已保存的唯一“默认环境”
if err != nil { return err }
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
page, err := browser.Read(ctx)
if err != nil { return err }
fmt.Println(page)
_, err = browser.Detach(ctx)
return err
```

上面是函数体片段，调用方需要 `context` 和 `fmt`。解析依赖前将 `GOMODCACHE`、`GOCACHE`、`GOTMPDIR` 指向 D 盘。[Go 说明](go/README.md) · [可运行 sample](go/examples/basic/main.go)。在 `go/` 目录执行 `go run ./examples/basic --live`。

## 让 AI Agent 通过 MCP 操作浏览器

推荐通过管理器的 **Agent 接入** 页面，将 MCP 安装到支持的 Agent 中。支持手动配置 stdio 的客户端，也可按其配置格式填写：

```json
{
  "mcpServers": {
    "kingai-browser": {
      "command": "D:\\Apps\\KingAIBrowser\\KingAIMcpServer.exe",
      "args": []
    }
  }
}
```

替换实际路径，并在 Agent 中确认连接。具体工具及参数以安装版 `tools/list` 为准。支持相应能力的版本提供 Skill 工具：`skills_list`、`skill_describe`、`skill_run`、`skill_status`、`skill_cancel`。

可以对 Agent 说：“打开我保存的‘资料整理’指纹环境，访问 example.com，读取页面内容，完成后保留浏览器。”

![管理器中的 Agent 接入](images/mcp-skill-run.png)

## Sample 与测试

示例命令和测试调用同一个可复用 sample 函数。真实运行必须明确传入 `--live`；同步示例会创建持久环境并在结束时 detach，窗口保留。同名环境重复运行可能报重名错误；异步示例使用已保存默认环境。

源 SDK 此前在 Windows 下通过 **17 项模拟 MCP 测试**：Python 7、Node.js 4、Java 3、Go 3，覆盖 stdio 通信、sample 流程、部分 CRUD 错误、不自动重放、操作与观察锁、预览大小控制。**本次公开仓库整理和 Go module 路径调整后未重新运行测试。** 这些测试不证明真实网页、指纹检测或会员票据已验证。

详见 [SAMPLES.md](SAMPLES.md)。安装 Python、Node.js、Java、Maven、Go 后可手动执行：

```powershell
.\tests\Run-Samples.ps1 -GoExecutable go -MavenCommand mvn.cmd
```

脚本将依赖、缓存和输出放 D 盘，不构建 Chromium 或 Rust。缺少测试 MCP 路径时，测试不会回退连接真实账号与浏览器。

## 接口约定

- `tools` / `Tools` 发现工具，`call` / `Call` 调用已安装 MCP 的能力。原始请求字段保留 snake_case，返回 ID 保留 `sessionId`、`targetId` 等命名。
- 不指定环境的 `start()` 选择已保存的唯一“默认环境”，缺失时不会自动创建。临时环境需明确请求。
- 客户端 close 断开自己的 MCP；会话的显式关闭方法才会关闭浏览器。环境 CRUD 要求登录及兼容 MCP/Runtime。
- 账号额度按同时打开的指纹环境数量限制，与点击数或 SDK 调用次数无关。humanize 请求标志或元数据不代表实际获得权益。
- 输入可能要求选中页面可见。`PAGE_NOT_VISIBLE` 时恢复窗口并激活目标标签页。
- 会话基于选中标签页操作，多步流程应串行；不提供 Playwright 多 Page 对象兼容。
- 超时或断线不证明操作未发生，SDK 不自动重试副作用；大结果使用显式预览方法。

[API 契约](CONTRACT.md) · [源码安装与发布说明](RELEASE.md) · [反馈问题](https://github.com/KingOX-cpp/KingAIBrowser/issues)。提交日志前请移除密钥、账号与隐私信息。

## 开源许可

客户端 SDK 使用 [BSD-3-Clause](LICENSE)，保留已有版权声明。浏览器软件和第三方依赖按各自条款提供。本仓库未引入 CloakBrowser 源码。
