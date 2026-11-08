import { KingAI, discoverMcp } from './client.mjs';

/** Inspect installation and MCP capabilities without launching a browser. */
export async function doctor(mcpExecutable) {
  const report = {
    clientVersion: '0.3.1', status: 'ok', checks: [],
    login: { status: 'unknown', reason: 'No read-only authentication tool is exposed by this SDK contract' },
    runtime: 'not_verified', stderr: 'forwarded_to_parent_stderr',
  };
  let api;
  try {
    report.mcpExecutable = await discoverMcp(mcpExecutable);
    api = new KingAI({ mcpExecutable: report.mcpExecutable, timeoutMs: 15000 });
    await api.connect();
    report.server = api.serverInfo;
    report.tools = (await api.tools()).map(tool => tool.name).sort();
    report.missingRecommendedTools = ['browser_start', 'browser_query', 'profiles_list', 'sdk_info']
      .filter(name => !report.tools.includes(name));
    if (report.tools.includes('sdk_info')) report.api = await api.info();
    else report.checks.push('This older MCP does not expose sdk_info; existing tools may still work');
    if (report.missingRecommendedTools.length) report.status = 'warning';
    report.checks.push('MCP handshake and tools/list completed; browser and Runtime were not started');
  } catch (error) {
    report.status = 'error';
    report.error = { code: error.code ?? 'DOCTOR_FAILED', message: error.message };
    report.checks.push(
      'Verify the installed MCP path and its sibling Runtime executable',
      'Inspect parent stderr and any Windows loader dialog for missing VC++ runtime DLLs',
      'For RUNTIME_ELEVATION_MISMATCH, follow the permissions troubleshooting guide; do not force-kill active browsers',
    );
  } finally { await api?.close(); }
  return report;
}
