# KingAI Java SDK

Java 17+，Maven 模块，版本 0.3.0。该库直接使用 JSON-RPC/stdin/stdout 连接已安装 KingAI MCP；不需要 Python、Node.js 或 HTTP 服务。JSON 编解码使用 Jackson。sample 与 3 项测试已在模拟 MCP 下通过，入口及复跑方法见 [SAMPLES](../SAMPLES.md)。

```java
import cn.kingaibrowser.sdk.KingAI;

try (KingAI api = new KingAI()) {
    System.out.println(api.info());
    KingAI.Session browser = api.start(); // 已有唯一“默认环境”
    browser.newTab("https://example.com");
    System.out.println(browser.read());
    browser.detach();
}
```

显式配置：`KingAI.Options o = new KingAI.Options(); o.mcpExecutable = Path.of("绝对MCP路径"); new KingAI(o)`。还支持 timeout、language、fileRoots、downloadDir 和 artifactDir。

环境管理使用 profiles/profile/createProfile/updateProfile/deleteProfile；删除必须显式确认。`api.tools()` 返回全部 schema；`api.call(name, Map.of(...))` 调用所有 MCP 工具；`session.call` 绑定会话。`session.observe(name,args)` 对操作和观察整体加锁。`evaluatePreview` 使用随 JAR 分发的资源脚本，不能只复制 Java 类而丢失 resources。

`api.close()` 只关闭自己的 MCP；`session.closeBrowser()` 明确关闭浏览器。超时或线程中断不代表副作用未发生，不自动重试。`KingAIException` 保留 code/details/outcomeUnknown。请使用 try-with-resources；没有安装全局 JVM shutdown hook。

Maven 坐标是本地发布准备值，尚未发布到 Maven Central。D 盘仓库/构建目录参数及发布约束见 [RELEASE](../RELEASE.md)，共同 API 规则见 [CONTRACT](../CONTRACT.md)。本轮测试没有启动真实浏览器，也未验证其他平台组合。
