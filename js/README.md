# KingAI Node.js / TypeScript SDK

[English project README](../README.md) · [中文项目介绍](../README.zh-CN.md) · [Complete examples](../examples/README.md)

Node.js 22+, ESM, TypeScript declarations included. Calls the installed KingAI MCP server over stdio. No Playwright or HTTP service required.

From your application, install this directory:

```powershell
npm install --cache D:\code\kingai-sdk-cache\npm D:\code\KingAIBrowser\js
```

```javascript
import { KingAI } from '@kingai/browser-api';
const api = new KingAI();
try {
  console.log(await api.profiles());
  const browser = await api.start(); // existing saved 默认环境
  await browser.newTab('https://example.com');
  console.log(await browser.snapshot());
  await browser.detach();
} finally { await api.close(); }
```

For the complete workflow, serve the shared playground as described in [examples](../examples/README.md), install dependencies in this js/ directory, then run `node examples/workflow.mjs --live`. It lists/creates/configures a profile, observes DOM, fills inputs, clicks submit and confirms the result. `examples/node.mjs` remains a minimal connection example.

The npm package has not been published. MIT licensed; preserve the license and applicable third-party notices. Tests live in tests/; repository-level orchestration is in ../tests/Run-Samples.ps1. Repository reorganization and new live workflows have not been executed in this task.
