# KingAI Python SDK 0.3.0

Requires Python 3.10+ and a compatible, installed KingAI MCP/Runtime/browser.
This package does not download a browser or expose CDP/HTTP. All quota and
humanization decisions remain in the existing account/Runtime/browser layers.

Complete environment/DOM/input/click workflow: [examples/workflow.py](examples/workflow.py).
See the [shared playground and run instructions](../examples/README.md) first.

```python
from kingai_browser import KingAI

with KingAI() as api:
    print(api.info())
    print(api.profiles())
    # Explicit creation, not a fallback if a default environment is missing:
    profile = api.create_profile("代码演示")
    browser = api.start(profile_id=profile["profileId"])
    browser.new_tab("https://example.com")
    print(browser.snapshot())
    browser.detach()
```

Async API (same core; I/O is dispatched to a worker, not the event loop):

```python
import asyncio
from kingai_browser import AsyncKingAI

async def main():
    async with AsyncKingAI() as api:
        browser = await api.start()  # existing unique 默认环境
        await browser.goto("https://example.com")
        print(await browser.read())
        await browser.detach()

asyncio.run(main())
```

Specify `mcp_executable=...`, set `KINGAI_MCP_EXECUTABLE`, or open the updated
Manager once for per-user discovery. `info()` requires the new `sdk_info` tool;
CRUD requires the updated MCP/Runtime. `tools()` discovers the actual server API.

`browser.click(ref="observed-ref", observe=True)` keeps operation and observation
exclusive on that SDK client. Use only actual fresh refs. `evaluate()` retains
raw semantics; `evaluate_preview()` explicitly bounds its result. A truncated
preview is not complete data. No automatic retries/reconnects occur. Cancelling
an async await does not undo an already-dispatched operation; the facade waits
for the worker before releasing its lock.

`from kingai_browser import BrowserAutomation` provides the optional agent
action interface (`execute`, `get_current_state`, `describe_error`, `close`).
It has no OpenManus/Pydantic dependency. Raw `call()` still exposes every MCP tool.

`api.close()` disconnects the owned MCP; `browser.close()` explicitly closes a
browser. Unattended authentication is not performed by this package. Sign in to
the installed KingAI account first. The synchronous and asynchronous samples
passed 7 tests against a simulated MCP server; see [SAMPLES](../SAMPLES.md).
Real-browser behavior and package installation remain unverified. The package
has not been published to PyPI.
