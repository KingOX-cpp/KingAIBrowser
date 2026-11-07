/** Read-only catalog of every tool exposed by the installed MCP.
 * 中文：读取工具说明和输入 schema，不执行工具，不启动环境浏览器。
 * Run: node js/examples/mcp_tool_catalog.mjs [browser_query]
 */
import { KingAI } from '../client.mjs';

const requestedName = process.argv[2];
const api = new KingAI();
try {
  // tools() follows server pagination. Do not replace this with a stale list.
  const tools = await api.tools();
  const selected = tools.filter(tool => !requestedName || tool.name === requestedName);
  if (!selected.length) throw new Error(`Tool unavailable: ${requestedName}`);
  for (const tool of selected) {
    console.log(`\n=== ${tool.name} ===`);
    console.log(tool.description ?? '');
    console.log(JSON.stringify(tool.inputSchema ?? {}, null, 2));
  }
} finally {
  // Always release this client's MCP, including schema/discovery failures.
  await api.close();
}
