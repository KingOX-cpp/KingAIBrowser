# KingAI code API contract 1 / SDK 0.3.0

源码交付日期：2026-11-06。实现语言：Python、Node.js/TypeScript、Java、Go。
本文定义代码契约，不是已通过测试的报告。所有客户端共用 stdio MCP、Runtime、账号并发额度和浏览器输入层。

## 能力与版本协商

`sdk_info` 是本次新增的本地 MCP 工具，不启动 Runtime/浏览器，返回 `sdkApiVersion: 1`、serverVersion、features、transport 和 rawCdp。features 描述 MCP 入口，`runtimeVerified:false` 明确表示此只读本地查询没有验证正在运行的 Runtime 是否已更新；不能用它代替 MCP/Runtime 成套分发。
四种 SDK 均有通用 `call`/`Call`，能调用实际 MCP `tools/list` 中的全部工具；便利方法不复制内核执行逻辑。

| 能力 | Python | Node.js/TS | Java | Go |
| --- | --- | --- | --- | --- |
| 一行保存环境入口 | launch(profile_id=...) | launch({profileId}) | KingAI.launch(options, profileId) | Launch(ctx, options, profileID) |
| 全部 MCP 工具发现/调用 | tools / call | tools / call | tools / call | Tools / Call |
| 保存环境 CRUD | profile / create_profile / update_profile / delete_profile | profile / createProfile / updateProfile / deleteProfile | profile / createProfile / updateProfile / deleteProfile | Profile / CreateProfile / UpdateProfile / DeleteProfile |
| 会话/标签页/输入/读取 | 有 | 有 | 有 | 有 |
| 操作后观察并持有客户端锁 | observe=True | observe:true | session.observe | session.Observe |
| 原始求值 / 显式预览 | evaluate / evaluate_preview | evaluate / evaluatePreview | evaluate / evaluatePreview | Evaluate / EvaluatePreview |
| Agent action facade | BrowserAutomation | BrowserAutomation | 通用工具调用 | 通用工具调用 |
| 异步 | AsyncKingAI | Promise | 可由调用方放入其 Executor | context + goroutine |
| 状态恢复/Skill/文件/网络等 | 通用工具 + 部分便利方法 | 同左 | 同左 | 同左 |

旧 MCP 仍可使用它已有的工具，不能因 SDK 更新就假定服务端具备新能力。新 CRUD 和 sdk_info 需要用户编译、分发当前 MCP 与 Runtime；根据 tools/list 发现能力，不根据套餐显示名称或文件名推断。
SDK 0.3.0 不承诺与标准 Playwright Browser/Page 对象互换。默认一个会话选择一个标签页，多步操作需同客户端 exclusive/Observe；页面自身异步变化不受客户端锁控制。

## 请求与结果

- 工具参数保留 snake_case。SDK 方法按语言习惯命名，不能递归转换业务 JSON。
- 会话/标签页结果保留后端 `sessionId`、`targetId` 等 camelCase 字段。
- 工具名及 inputSchema 以安装版 `tools/list` 为准；分页 cursor 由服务器生成，不解析或猜测。
- MCP JSON-RPC 请求 ID 不等于 Runtime 请求 ID。只有后端返回的 Runtime ID 可以用于 runtime_request_status。
- 不返回内部 DevTools 端口/Token、Lease Secret、会员票据、完整指纹 JSON。

## 保存环境 CRUD

| MCP 工具 | 参数 | 结果 |
| --- | --- | --- |
| profiles_list | 空对象 | 已有 Dashboard（profiles/groups 等） |
| profiles_get | profile_id | 与列表同种 ProfileSummary，不含完整配置 |
| profiles_create | name，选填 group_name/language | profileId |
| profiles_update | profile_id，选填 name/group_name/patch | profileId、updated |
| profiles_delete | profile_id、显式 confirm=true | profileId、deleted |

管理动作要求已有登录账号。创建只创建保存环境，不打开浏览器、不消耗额外“执行次数”。名称沿用核心的去空格/忽略大小写唯一约束；分组必须符合现有分组规则。删除不得关闭正在运行的环境，仍保留至少一个环境，并删除该环境保存数据；不能用作 Agent 回合清理。

更新只允许关闭的环境，在环境锁内执行读/合并/校验/保存。patch 是递归对象合并；数组整体替换，null 为显式值，不表示删除键。允许的顶层配置面：identity、locale、hardware、display、graphics、canvas、audio、client_rects、plugins、media、network、privacy、fonts、storage。各顶层值必须是对象，补丁最大 256 KiB、递归深度最大 16；不能提交 runtime、授权、schema_version、profile_id 等受保护部分。配置字段沿用管理器既有配置格式，见 `../fingerprint_config.example.json`。

例如修改语言/时区和设备参数（其他字段保持已有值；地区/代理/语言必须一致）：

```json
{"profile_id":"saved-profile-uuid","patch":{"locale":{"language":"zh-CN","accept_languages":"zh-CN,zh","timezone":"Asia/Shanghai"},"hardware":{"hardware_concurrency":8,"device_memory_gb":8}}}
```

代理密码可通过受保护 IPC 的补丁输入，在核心凭据存储内保存，不返回给调用者。更新前读取的既有秘密在内存中保留，避免仅改名称就删除已有代理密码。SDK 不日志记录输入配置；调用方也不应打印带密码的请求。

## 启动、授权与计费

普通 start 查找已有唯一“默认环境”。缺失或名称歧义报错，不自动创建。创建默认环境必须显式调用 profiles_create（name 为默认环境）后启动。临时环境需要显式 temporary=true。

额度按账号同时打开的指纹环境数量计算，与点击、工具调用或工作流数量无关。四种 SDK 均调用原 MCP 入口，不新增收费计数或临时授权池。humanize、票据刷新、同步争用、Lease 与 Runtime 权限路径沿用现有核心。

## 发现与生命周期

优先显式 MCP 路径，其次 KINGAI_MCP_EXECUTABLE，然后用户登记文件。Windows 为 `%LOCALAPPDATA%/KingAIBrowser/sdk-installation.json`，macOS 为 `~/Library/Application Support/KingAIBrowser/sdk-installation.json`。Manager 启动登记当前安装；多套安装使用显式路径。只读小型位置记录不构成同用户恶意程序隔离或软件签名证明。

客户端仅启动自己的 MCP，Runtime 仍由已有连接路径按需启动；不会执行 shell、搜索 PATH 或自动下载另一套内核。客户端传最小系统环境和显式目录设置，不传宿主全部环境。

客户端 close 只断开该客户端的 MCP，浏览器关闭是独立明确动作。launch 返回会话拥有其新建的客户端；Python with launch() 和 Java try-with-resources Session 退出时 detach 并释放客户端，保留浏览器窗口。非 owned Session 的自动资源退出不接管外部客户端或关闭浏览器。Python close()/close_browser()、Node close()/closeBrowser()、Go Close()/CloseBrowser() 仍显式关闭浏览器；Java 显式关闭用 closeBrowser()，Session.close() 仅作上述自动资源清理。已 detach 的 owned 会话不应再次自动 detach。

显式创建客户端时，Java try-with-resources KingAI、Go defer Client.Close、Python with/async with KingAI、Node try/finally 仅管理客户端连接。SDK 不按进程名杀 Runtime/浏览器或进程树。强制结束后的行为仍需实际回归，不能承诺所有异常退出均完成清理。

Java waitFor/type/hover 和 click/fill 的 options 重载、Go Wait/Type/Hover 和 Click/Fill 的可选 options 支持高层输入；humanize 可显式传 false。Java 使用 waitFor 避免混淆 Object.wait。Python、Node、Go 的会话 close/Close 仍显式关浏览器；Java Session.close 用于自动资源清理，显式关浏览器必须调用 closeBrowser。客户端 close 与会话关闭含义不同，不能仅凭同名方法推断行为。

owned 会话 detach 或释放客户端后，原对象不可继续控制保留的窗口。需要关闭时，可在管理器操作，或通过新客户端发现实际会话并在授权允许时显式 attach，再调用浏览器关闭方法。Java closeBrowser 在客户端已关闭时抛 SESSION_DISCONNECTED，不返回 null，也不自动重连或重放。

Python/Node CLI doctor 只执行定位、初始化、tools/list 与可选 sdk_info，不启动 Runtime/浏览器。登录态未知和 Runtime 未验证必须如实显示。MCP stderr 转发到调用方 stderr，不持久化；共享诊断前由用户脱敏。新增入口、诊断和生命周期用例本轮未执行验证。

## 操作与观察

observe 组合在同客户端独占范围内执行：操作一次 → 读取 page/snapshot/tabs。返回 operationResult、businessOutcome=not_verified、observationStatus。观察失败单独报告，不将已派发点击改成执行失败，不重放前面的输入。

humanizationRequiresEntitlement=true 只是能力依赖说明，不证明会员失效或实际拟人化生效。PAGE_NOT_VISIBLE 仍要求激活目标标签页并恢复窗口。

evaluate 保留原始语义。evaluate_preview/evaluatePreview/EvaluatePreview 显式启用预览：文本预算 12000 字符、单字符串 1000、每容器 40 项、深度 5、节点 500。原表达式只执行一次；该预算限制返回序列化，不限制原脚本计算量或副作用。truncated=true 必须显式对只读数据分页，不能把预览当完整数据。

## 错误与取消

保留后端 code/message/details。RESULT_TOO_LARGE 是“求值已执行但返回过大”，不是自动重试信号。INVALID_TOOL_RESPONSE、连接中断或超时可能发生在副作用之后，不能推断失败或自动重放。

Python AsyncKingAI 通过 worker 调用同步 SDK，取消 await 不会撤回已发送输入；会等 worker 完成再释放锁。Go 使用 context 限制调用，取消不撤销页面副作用。Java 超时/中断、Node Promise 拒绝也没有自动重放。不是持久任务调度器，也不承诺 exactly-once。
