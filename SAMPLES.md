# Samples 与验证结果

源 SDK 验证日期：2026-11-06。以下结果来自迁入本仓库前的源 SDK；本仓库整理、Go module 路径和 js/ 目录调整后未重新测试。以下单元测试对应原有最小 sample 函数。新增的四语言完整 workflow 包含 DOM 查询、输入、点击与结果确认，见 [examples/README.md](examples/README.md)，本轮未运行或测试。

| 语言 | Sample 实现 | 测试 | 本轮结果 |
| --- | --- | --- | --- |
| Python 同步 | python/examples/sync.py 的 run_sample | python/tests/test_samples.py | 与异步合计 7 项通过 |
| Python 异步 | python/examples/async.py 的 run_sample | 同上 | 包含实际异步 sample、取消不重放 |
| Node.js | js/examples/node.mjs 的 runSample | js/tests/samples.test.mjs | 4 项通过 |
| Java | java/src/main/java/cn/kingaibrowser/sdk/samples/Sample.java | java/src/test/java/cn/kingaibrowser/sdk/SampleTest.java | 3 项通过 |
| Go | go/sample/sample.go 的 RunSample | go/sample_test.go | 3 项通过 |

共 **17 项通过，0 失败、0 跳过**。测试经过真实 SDK 的 stdio 通信，连接 tests/fixture/main.go 编译的专用模拟 MCP。模拟器只有内存状态，不读取真实数据库、账号或票据，不启动浏览器，不连接网站。

## 验证范围

- sample：查询环境、创建环境、启动会话、新建标签访问 example.com、读取页面、求值预览、detach。
- Python 异步 sample：默认环境、新标签、读取、detach。
- CRUD：读取/更新、删除确认、运行中更新拒绝，以及显式关闭后的删除。
- 异常：保留 RESULT_TOO_LARGE，不自动重跑；非 JSON 文本归为 INVALID_TOOL_RESPONSE。
- 锁：Python/Node 并发调用时，“点击→读取→快照→标签页”不会交错。
- 预览：用 Node VM 实际执行 Node、Java、Go 分发的预览脚本，确认可执行、带截断标记且结果低于 256 KiB。
- sample 不自动关闭浏览器；命令行真实运行需要显式 --live。

这证明调用示例、SDK 封装和上述通信/错误行为在模拟服务下有效。**没有验证真实浏览器渲染、会员票据、指纹效果、网站兼容性，也没有构建或测试 Rust MCP/Runtime、Chromium。**

## 复跑全部 sample 测试

Windows PowerShell，需 Python 3.10+、Node 22+、Java 17+、Go 1.24+、Maven。默认从 PATH 查找 Go/Maven，可通过参数指定已安装工具；测试依赖与输出默认放在 D:\code\kingai-sdk-validation：

```powershell
.\tests\Run-Samples.ps1
# 或：
.\tests\Run-Samples.ps1 -GoExecutable 'D:\tools\go\bin\go.exe' -MavenCommand 'D:\tools\maven\bin\mvn.cmd'
```

脚本只编译测试模拟器和 SDK 的 Java/Go 测试，绝不运行 GN、Chromium 或 Rust 构建。依赖、缓存、Go/Node 源码快照和构建输出均放 D 盘；环境变量退出时恢复，不清理已有浏览器或构建目录。缺少 KINGAI_TEST_MCP 时，各语言测试会明确跳过，不能把跳过算通过。

## 手动运行真实 sample

先安装相应 SDK、登录 KingAI，并更新兼容的 MCP/Runtime。设置 KINGAI_MCP_EXECUTABLE，或使用已有 Manager 路径登记。真实 sample 会创建持久环境，重复使用相同名称会返回重名错误，正常结束只 detach、不删除环境。

- Python：`python python/examples/sync.py --live`；异步：`python python/examples/async.py --live`（异步使用已有默认环境）。
- Node.js：`node js/examples/node.mjs --live`（先安装依赖）。
- Java：运行 `cn.kingaibrowser.sdk.samples.Sample --live`，或 java/examples/Example.java 转发入口；classpath 需要本库及 Jackson 依赖。
- Go：在 go 目录运行 `go run ./examples/basic --live`。

这些真实 sample 没有在本任务执行；不会把模拟器测试结论冒充真实浏览器验证。
