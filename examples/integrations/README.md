# Agent integration over stdio MCP

Use [stdio_agent_config.json](stdio_agent_config.json) as a configuration template for an agent client supporting the mcpServers stdio format. Replace command with the actual installed MCP executable, with KingAIRuntime.exe beside it. This is a template, not an automatically installed or verified integration for every framework.

1. Install KingAI Browser, sign in and create/select a saved environment in Manager.
2. Prefer Manager's Agent integration page for supported clients. For manual integration, copy the server entry into the client's documented MCP configuration location.
3. Restart/reload that client, approve the local server connection and inspect its tools list.
4. Ask: "List saved environments. Open profile UUID, visit example.com and read the page. Keep the browser open when finished."
5. Confirm the agent selects an actual returned profile ID, rather than inventing one. Temporary environments require explicit permission/request.

No SDK package, DevTools URL, CDP port or Playwright connection is required by this path. The agent owns its MCP subprocess; the installed Runtime enforces account limits and profile ownership. If another automation owns the environment, do not force takeover. Do not add credentials or API tokens to this template.

## 中文说明

本模板适用于支持 mcpServers stdio 配置的 Agent 客户端。请替换真实程序路径，按客户端自己的文档放入配置；管理器已支持的 Agent 优先通过“Agent 接入”安装。连接后先发现工具与环境列表，再使用真实环境 ID 执行任务。不能把本模板视为所有 Agent 框架都已实测。

This integration example has not been executed in this change. Use [doctor and troubleshooting](../../TROUBLESHOOTING.md) for read-only installation diagnostics.
