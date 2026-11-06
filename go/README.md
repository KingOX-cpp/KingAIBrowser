# KingAI Go SDK

完整环境、DOM、输入和点击示例：[workflow/main.go](examples/workflow/main.go)，运行说明见[示例导航](../examples/README.md)。

Go 1.24+，module 为 `github.com/KingOX-cpp/KingAIBrowser/go`，使用官方 MCP Go SDK v1.4.0。module 对应本仓库的 go 子目录，尚未发布版本标签，可先通过本地 replace 使用。已纳入 go.sum；源 SDK 的 3 项模拟 MCP 测试此前通过，本仓库调整后未重新测试。入口及复跑方法见 [SAMPLES](../SAMPLES.md)。

```go
api, err := kingai.Connect(ctx, kingai.Options{})
if err != nil { return err }
defer api.Close()
browser, err := api.Start(ctx, nil) // 已有唯一“默认环境”
if err != nil { return err }
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
page, err := browser.Read(ctx)
if err != nil { return err }
fmt.Println(page)
_, err = browser.Detach(ctx)
return err
```

完整示例在 examples/basic/main.go。调用项目 go.mod 可通过 `replace github.com/KingOX-cpp/KingAIBrowser/go => 本地绝对目录` 引用本库，再按用户环境解析依赖。解析依赖前将 GOMODCACHE/GOCACHE/GOTMPDIR 放 D 盘，详见 [RELEASE](../RELEASE.md)。

Options 提供 MCPExecutable、Timeout、Language、FileRoots、DownloadDir、ArtifactDir。省略路径时读取 KINGAI_MCP_EXECUTABLE 或 Manager 安装登记，不扫描磁盘或下载浏览器。

Profiles/Profile/CreateProfile/UpdateProfile/DeleteProfile 提供环境管理。Tools 返回完整 schema，Call(ctx,name,args) 调用全部 MCP 工具；Session.Call 绑定会话。Session.Observe 整体持有客户端锁，Evaluate 保留原始语义，EvaluatePreview 显式预览。更多截图、输入、Cookie、Storage、文件及 Skill 能力见便利方法或通用 Call。

Client.Close 断开自己的 MCP；Session.Close 明确关闭浏览器。context 取消不会撤回已派发输入，错误也不会触发自动重试或自动重连。Error 包含 Code/Details/OutcomeUnknown。多进程额度仍由原账号 Lease 统一管理，见 [CONTRACT](../CONTRACT.md)。
