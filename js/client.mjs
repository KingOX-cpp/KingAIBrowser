/** KingAI code API over the SAME installed stdio MCP used by Agents. */
import { dirname } from 'node:path';
import { AsyncLocalStorage } from 'node:async_hooks';
import { observeOperation, previewExpression } from './observation.mjs';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { ErrorCode, McpError } from '@modelcontextprotocol/sdk/types.js';
import { childEnvironment, decodeTool, discoverMcp, KingAIError } from './discovery.mjs';
export { discoverMcp, KingAIError };
export { BrowserAutomation } from './automation.mjs';
export { install } from './installer.mjs';
const scopes = new AsyncLocalStorage();

export async function launch({ profileId, headless = false, temporary = false, ...clientOptions } = {}) {
  const api = new KingAI(clientOptions);
  try {
    const browser = await api.start({ ...(profileId === undefined ? {} : { profile_id: profileId }), headless, temporary });
    browser._ownsClient = true;
    return browser;
  } catch (error) {
    await api.close();
    throw error;
  }
}

export class KingAI {
  constructor({ mcpExecutable, timeoutMs = 360000, language, fileRoots, downloadDir, artifactDir } = {}) {
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new TypeError('timeoutMs must be positive and finite');
    this._executable = mcpExecutable;
    this._timeoutMs = timeoutMs;
    this._env = childEnvironment({ language, fileRoots, downloadDir, artifactDir });
    this._closed = false;
    this._dead = false;
    this._connection = undefined;
    this._queue = Promise.resolve();
  }

  async connect() {
    if (this._closed) throw new KingAIError({ code: 'CLIENT_CLOSED', message: 'Create a new KingAI client after close()' });
    if (this._dead) throw new KingAIError({ code: 'MCP_DISCONNECTED', message: 'Create a new KingAI client; no automatic reconnection was attempted' });
    this._connection ??= this._open();
    await this._connection;
    if (this._closed || this._dead) throw new KingAIError({ code: 'MCP_DISCONNECTED', message: 'The MCP connection is closed' });
    return this;
  }

  async _open() {
    try {
      const command = await discoverMcp(this._executable);
      if (this._closed) throw new Error('Client closed during discovery');
      this._transport = new StdioClientTransport({ command, cwd: dirname(command), env: this._env, stderr: 'inherit' });
      this._client = new Client({ name: 'kingai-node', version: '0.3.1' }, { capabilities: {} });
      this._client.onclose = () => { this._dead = true; };
      await this._client.connect(this._transport, { timeout: this._timeoutMs });
      if (!this._client.getServerCapabilities()?.tools) throw new Error('The installed MCP server does not advertise tools');
      this.serverInfo = this._client.getServerVersion();
    } catch (cause) {
      this._dead = true;
      await this._transport?.close().catch(() => {});
      if (cause instanceof KingAIError) throw cause;
      throw new KingAIError({ code: 'MCP_START_FAILED', message: 'Could not start or initialize the installed MCP executable', reason: String(cause) });
    }
  }

  _enqueue(work) {
    const scope = scopes.getStore();
    if (scope?.client === this && scope.active) {
      const result = scope.tail.then(work);
      scope.tail = result.catch(() => {});
      return result;
    }
    const result = this._queue.then(async () => {
      await this.connect();
      return work();
    });
    this._queue = result.catch(() => {});
    return result;
  }

  exclusive(work) {
    const existing = scopes.getStore();
    if (existing?.client === this && existing.active) return Promise.resolve().then(() => work(this));
    return this._enqueue(() => {
      const scope = { client: this, active: true, tail: Promise.resolve() };
      return scopes.run(scope, async () => {
        try { return await work(this); }
        finally { await scope.tail; scope.active = false; }
      });
    });
  }

  async tools() {
    return this._enqueue(async () => {
      const tools = [], cursors = new Set();
      let cursor;
      do {
        const result = await this._client.listTools(cursor === undefined ? {} : { cursor }, { timeout: this._timeoutMs });
        tools.push(...result.tools);
        cursor = result.nextCursor;
        if (cursor !== undefined) {
          if (typeof cursor !== 'string' || cursors.has(cursor)) throw new KingAIError({ code: 'INVALID_TOOL_RESPONSE', message: 'MCP returned an invalid or repeated tool-list cursor' });
          cursors.add(cursor);
        }
      } while (cursor !== undefined);
      return tools;
    });
  }

  call(name, args = {}) {
    if (typeof name !== 'string' || !/^[a-z][a-z0-9_]*$/.test(name)) throw new TypeError('Invalid tool name');
    if (!args || typeof args !== 'object' || Array.isArray(args)) throw new TypeError('Tool arguments must be an object');
    // Snapshot arguments before queuing. Serialization errors happen before dispatch.
    const argumentsCopy = JSON.parse(JSON.stringify(args, (_key, value) => {
      if (typeof value === 'number' && !Number.isFinite(value)) throw new TypeError('Arguments must contain finite JSON numbers');
      return value;
    }));
    return this._enqueue(async () => {
      let result;
      try {
        result = await this._client.callTool({ name, arguments: argumentsCopy }, undefined, { timeout: this._timeoutMs });
      } catch (cause) {
        if (cause instanceof McpError && cause.code !== ErrorCode.RequestTimeout && cause.code !== ErrorCode.ConnectionClosed) {
          throw new KingAIError({ code: 'MCP_PROTOCOL_ERROR', message: cause.message, rpcCode: cause.code, rpcData: cause.data, outcomeUnknown: true });
        }
        // A lost response must never trigger automatic replay or a new browser.
        throw new KingAIError({ code: 'OUTCOME_UNKNOWN', message: 'MCP call did not return a usable response. Inspect session state before repeating an action.', outcomeUnknown: true, reason: String(cause) });
      }
      return decodeTool(result);
    });
  }

  async close() {
    if (this._closed) return;
    this._closed = true;
    // Close only the owned stdio transport, never Runtime or browser windows.
    // Closing while initialization is in progress is completed by _open below.
    if (this._transport) await this._transport.close();
    if (this._connection) {
      await this._connection.catch(() => {});
      await this._transport?.close();
    }
  }

  profiles() { return this.call('profiles_list'); }
  info() { return this.call('sdk_info'); }
  profile(profileId) { return this.call('profiles_get', { profile_id: profileId }); }
  createProfile(name, options = {}) { return this.call('profiles_create', { ...options, name }); }
  updateProfile(profileId, options = {}) { return this.call('profiles_update', { ...options, profile_id: profileId }); }
  deleteProfile(profileId, { confirm = false } = {}) { return this.call('profiles_delete', { profile_id: profileId, confirm }); }
  sessions() { return this.call('browser_sessions_list'); }
  async start(options = {}) {
    const info = await this.call('browser_start', options);
    if (!info || typeof info.sessionId !== 'string' || !info.sessionId) throw new KingAIError({ code: 'INVALID_TOOL_RESPONSE', message: 'browser_start returned no sessionId; inspect sessions before restarting', outcomeUnknown: true });
    return new BrowserSession(this, info.sessionId, info);
  }
  async attach(sessionId) {
    const info = await this.call('browser_attach', { session_id: sessionId });
    return new BrowserSession(this, sessionId, info);
  }
  requestStatus(requestId) { return this.call('runtime_request_status', { request_id: requestId }); }
  skills() { return this.call('skills_list'); }
  describeSkill(skillId) { return this.call('skill_describe', { skill_id: skillId }); }
  runSkill(profileId, skillId, options = {}) { return this.call('skill_run', { ...options, profile_id: profileId, skill_id: skillId }); }
  skillStatus(runId) { return this.call('skill_status', { run_id: runId }); }
  cancelSkill(runId) { return this.call('skill_cancel', { run_id: runId }); }
  skillRuns() { return this.call('skill_runs_list'); }
}

/** One selected tab per session. Await each step; multi-step workflows are not transactions. */
export class BrowserSession {
  constructor(client, sessionId, info = {}) {
    if (typeof sessionId !== 'string' || !sessionId) throw new TypeError('sessionId must be a non-empty string');
    this.client = client; this.sessionId = sessionId; this.info = info;
  }
  call(name, args = {}) {
    const { observe = false, ...params } = args;
    const invoke = () => this.client.call(name, { ...params, session_id: this.sessionId });
    return observe ? this.client.exclusive(async () => observeOperation(this, name, await invoke())) : invoke();
  }
  tabs() { return this.call('tabs_list'); }
  newTab(url) { return this.call('tabs_new', url === undefined ? {} : { url }); }
  activateTab(targetId) { return this.call('tabs_activate', { target_id: targetId }); }
  closeTab(targetId) { return this.call('tabs_close', { target_id: targetId }); }
  goto(url) { return this.call('browser_navigate', { url }); }
  read(options = {}) { return this.call('browser_read', options); }
  snapshot(options = {}) { return this.call('browser_snapshot', options); }
  query(options = {}) { return this.call('browser_query', options); }
  click(selector, options = {}) { return this.call('browser_click', { ...options, ...(selector === undefined ? {} : { selector }) }); }
  fill(selector, text, options = {}) { return this.call('browser_fill', { ...options, text, ...(selector === undefined ? {} : { selector }) }); }
  type(selector, text, options = {}) { return this.call('browser_type', { ...options, text, ...(selector === undefined ? {} : { selector }) }); }
  evaluate(expression, options = {}) { return this.call('browser_evaluate', { ...options, expression }); }
  evaluatePreview(expression, options = {}) { return this.evaluate(previewExpression(expression, options.await_promise !== false), options); }
  wait(options = {}) { return this.call('browser_wait', options); }
  screenshot(options = {}) { return this.call('browser_screenshot', options); }
  scroll(deltaY, options = {}) { return this.call('browser_scroll', { ...options, delta_y: deltaY }); }
  key(key, options = {}) { return this.call('browser_key', { ...options, key }); }
  hover(selector, options = {}) { return this.call('browser_hover', { ...options, ...(selector === undefined ? {} : { selector }) }); }
  pdf(options = {}) { return this.call('browser_pdf', options); }
  cookies() { return this.call('cookies_list'); }
  storage(options = {}) { return this.call('storage_get', options); }
  upload(paths, selector, options = {}) { return this.call('browser_upload', { ...options, paths, ...(selector === undefined ? {} : { selector }) }); }
  download(selector, options = {}) { return this.call('browser_download', { ...options, ...(selector === undefined ? {} : { selector }) }); }
  async disconnect() {
    if (!this._ownsClient) throw new Error('This session does not own its client; close the client explicitly');
    await this.client.close();
  }
  async detach() {
    try { return await this.call('browser_detach'); }
    finally { if (this._ownsClient) await this.client.close(); }
  }
  async close() {
    try { return await this.call('browser_close'); }
    finally { if (this._ownsClient) await this.client.close(); }
  }
  closeBrowser() { return this.close(); }
}
