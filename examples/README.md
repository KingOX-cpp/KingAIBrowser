# Complete SDK workflows / 完整调用示例

These examples go beyond opening a tab. Each full workflow lists environments, creates an isolated saved environment, sets its language and updates its name before startup, opens the playground, reads DOM elements, fills two fields, clicks a button and independently checks the submitted result.

完整流程：获取环境列表 → 创建环境并设置语言 → 修改保存环境名称 → 按 ID 启动 → 新建标签 → 等待页面可见 → 获取交互快照和 DOM → 查询元素 `ref` → 输入姓名与消息 → 点击提交 → 等待并核对结果 → 获取标签列表 → detach 保留窗口。

## Layout / 目录

| Language | Complete workflow | Minimal connection sample |
| --- | --- | --- |
| Python | [workflow.py](../python/examples/workflow.py) | [sync.py](../python/examples/sync.py), [async.py](../python/examples/async.py) |
| Node.js | [workflow.mjs](../js/examples/workflow.mjs) | [node.mjs](../js/examples/node.mjs) |
| Java | [Workflow.java](../java/src/main/java/cn/kingaibrowser/sdk/samples/Workflow.java) | [Sample.java](../java/src/main/java/cn/kingaibrowser/sdk/samples/Sample.java) |
| Go | [workflow/main.go](../go/examples/workflow/main.go) | [basic/main.go](../go/examples/basic/main.go) |

## Start the local playground / 启动本地演示页面

Run this in a separate terminal from the repository root and keep it running:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory examples
```

The page is **http://127.0.0.1:8765/demo.html**. It only updates local DOM on submission; it does not send form data anywhere. The server only binds loopback. If 8765 is occupied, use another port and update the URL constant in the workflow you use. This HTTP server serves the demo HTML only; it is not an SDK transport or browser API service.

这里的本地 HTTP 服务只是静态演示网页，SDK 仍通过 stdio MCP 操作浏览器。首次请手动打开上面的地址，确认网页服务已经运行，然后执行 SDK 示例。

## Run / 运行

Install the browser and sign in, set `KINGAI_MCP_EXECUTABLE`, and install your language's SDK as explained in the project README. Run commands below from the repository root:

```powershell
# Python: install ./python first
python python/examples/workflow.py --live

# Node.js: install dependencies inside ./js first
node js/examples/workflow.mjs --live

# Go: configure dependency caches on D: before running
cd go
go run ./examples/workflow --live
```

Java requires the complete library and Jackson dependencies on the classpath. One Maven-based way (no global SDK installation needed):

```powershell
mvn -f java/pom.xml -Dmaven.repo.local=D:/code/kingai-sdk-cache/m2 -Dkingai.build.directory=D:/code/kingai-sdk-build/java package dependency:copy-dependencies -DincludeScope=runtime -DoutputDirectory=D:/code/kingai-sdk-build/java/dependency
java -cp 'D:\code\kingai-sdk-build\java\classes;D:\code\kingai-sdk-build\java\dependency\*' cn.kingaibrowser.sdk.samples.Workflow --live
```

These are commands for you to execute. No compilation, checks, tests or live workflows were run during this change.

## What the code demonstrates / 关键说明

- `profiles` lists saved environment summaries; `profile` fetches one. Create/update calls operate on saved settings **before** starting the environment. The sample uses language and name; it does not invent proxy/hardware patch field names. For advanced fingerprint configuration, use supported fields from the installed API/Manager.
- `snapshot` provides a bounded interactive observation; `query` returns actual DOM summaries in `elements`, including an opaque `ref` and optional bounded HTML. These are not serialized live DOM objects.
- Every action obtains a fresh ref from a query, requires a unique result, then uses that ref. Never hardcode refs from another session or earlier run. CSS selectors and role/name filters are alternative query inputs; installed tool schemas remain authoritative.
- Input uses real `browser_fill` / `browser_click` tools, not JavaScript assignment or `element.click()`. `evaluate` only reads the result text.
- `humanize:false` lets the local form demo run without a humanize entitlement. To demonstrate humanized input, explicitly enable it with a valid entitlement. Other account/environment access rules still apply.
- Waits have explicit conditions and timeouts. `actionDispatched` alone is not proof of form submission; the workflow waits for the page's submitted marker and compares the exact result text. It does not automatically repeat failed side effects.
- A new uniquely named saved environment is created on every run, avoiding edits to existing profiles. Windows and saved environments are retained for inspection. Repeated runs consume disk space; close/delete demo environments explicitly when finished. Deletion is not automatic.
- Keep the demo window restored and its intended tab active. For `PAGE_NOT_VISIBLE`, restore/activate it before continuing.

Existing fixture test results in [SAMPLES.md](../SAMPLES.md) apply to the earlier minimal samples, not these new complete live workflows. The new workflows and reorganized SDK paths have not been executed or tested in this task.
