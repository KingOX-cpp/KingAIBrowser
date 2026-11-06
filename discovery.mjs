import { open, realpath, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { basename, dirname, isAbsolute, join } from 'node:path';

export class KingAIError extends Error {
  constructor(details) {
    super(details.message || details.error || details.code || 'KingAI request failed');
    this.name = 'KingAIError'; this.code = details.code || 'KINGAI_ERROR'; this.details = details;
  }
}

export async function discoverMcp(executable) {
  let selected = executable ?? process.env.KINGAI_MCP_EXECUTABLE;
  if (selected === undefined) {
    const directory = process.platform === 'win32'
      ? (process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, 'KingAIBrowser') : null)
      : process.platform === 'darwin'
        ? join(homedir(), 'Library', 'Application Support', 'KingAIBrowser')
        : join(homedir(), '.config', 'KingAIBrowser');
    if (directory) {
      let handle;
      try {
        handle = await open(join(directory, 'sdk-installation.json'), 'r');
        const buffer = Buffer.alloc(65537);
        let size = 0;
        while (size < buffer.length) {
          const { bytesRead } = await handle.read(buffer, size, buffer.length - size, null);
          if (!bytesRead) break;
          size += bytesRead;
        }
        if (size > 65536) throw new Error('Discovery record too large');
        const record = JSON.parse(buffer.subarray(0, size).toString('utf8'));
        if (record?.schemaVersion !== 1 || typeof record.mcpExecutable !== 'string') throw new Error('Invalid discovery record');
        selected = record.mcpExecutable;
      } catch (error) {
        if (error.code !== 'ENOENT') throw new KingAIError({ code: 'MCP_DISCOVERY_INVALID', message: 'Open the current Manager to refresh SDK discovery, or pass mcpExecutable explicitly' });
      } finally { await handle?.close(); }
    }
  }
  if (selected === undefined) throw new KingAIError({ code: 'MCP_NOT_FOUND', message: 'Open the current Manager once, set KINGAI_MCP_EXECUTABLE, or pass the absolute mcpExecutable path' });
  const expected = process.platform === 'win32' ? 'KingAIMcpServer.exe' : 'KingAIMcpServer';
  if (typeof selected !== 'string' || !isAbsolute(selected) || basename(selected).toLowerCase() !== expected.toLowerCase()) {
    throw new KingAIError({ code: 'MCP_PATH_INVALID', message: 'Specify the absolute KingAIMcpServer executable path' });
  }
  try {
    const runtime = process.platform === 'win32' ? 'KingAIRuntime.exe' : 'KingAIRuntime';
    const [mcp, sibling] = await Promise.all([stat(selected), stat(join(dirname(selected), runtime))]);
    if (!mcp.isFile() || !sibling.isFile()) throw new Error('Incomplete installation');
    return await realpath(selected);
  } catch {
    throw new KingAIError({ code: 'MCP_NOT_INSTALLED', message: 'MCP or its sibling Runtime is missing; reopen the updated Manager or specify a complete installation' });
  }
}

export function childEnvironment({ language, fileRoots, downloadDir, artifactDir }) {
  const allowed = new Set(['systemroot', 'windir', 'systemdrive', 'comspec', 'pathext',
    'programfiles', 'programfiles(x86)', 'programw6432', 'programdata', 'userprofile',
    'appdata', 'localappdata', 'homedrive', 'homepath', 'username', 'userdomain',
    'temp', 'tmp', 'home', 'lang', 'lc_all', 'lc_ctype', 'tmpdir', 'display', 'wayland_display', 'xdg_runtime_dir']);
  const env = Object.fromEntries(Object.entries(process.env).filter(([key, value]) => value !== undefined && allowed.has(key.toLowerCase())));
  const root = process.env.SystemRoot || process.env.SYSTEMROOT || 'C:\\Windows';
  env.PATH = process.platform === 'win32' ? [join(root, 'System32'), root].join(';') : '/usr/bin:/bin:/usr/sbin:/sbin';
  if (language !== undefined) {
    if (typeof language !== 'string') throw new TypeError('language must be a string');
    env.KINGAI_MCP_LANGUAGE = language;
  }
  for (const [key, path] of [['KINGAI_MCP_DOWNLOAD_DIR', downloadDir], ['KINGAI_MCP_ARTIFACT_DIR', artifactDir]]) {
    if (path !== undefined) {
      if (typeof path !== 'string' || !isAbsolute(path)) throw new TypeError(`${key} must be an absolute path`);
      env[key] = path;
    }
  }
  if (fileRoots !== undefined) {
    if (!Array.isArray(fileRoots) || fileRoots.length > 128 || fileRoots.some(path => typeof path !== 'string' || !isAbsolute(path) || path.includes(';'))) {
      throw new TypeError('fileRoots must contain at most 128 absolute paths without semicolons');
    }
    env.KINGAI_MCP_FILE_ROOTS = fileRoots.join(';');
  }
  return env;
}

export function decodeTool(result) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    throw new KingAIError({ code: 'INVALID_TOOL_RESPONSE', message: 'MCP tool returned a non-object result', outcomeUnknown: true });
  }
  let envelope = result.structuredContent;
  if (!envelope || typeof envelope.ok !== 'boolean') {
    const text = (Array.isArray(result.content) ? result.content : [])
      .filter(part => part?.type === 'text' && typeof part.text === 'string').map(part => part.text).join('\n');
    try { envelope = JSON.parse(text); } catch { envelope = undefined; }
  }
  if (envelope && typeof envelope.ok === 'boolean') {
    if (!envelope.ok) throw new KingAIError(envelope);
    if (!result.isError) return envelope.result;
  }
  if (result.isError) throw new KingAIError({ code: 'MCP_TOOL_ERROR', message: 'MCP reported a tool error', mcpResult: result });
  throw new KingAIError({ code: 'INVALID_TOOL_RESPONSE', message: 'MCP returned no valid KingAI result envelope; inspect state before repeating the operation', outcomeUnknown: true, mcpResult: result });
}
