# SDK entry points across all four languages

English | [简体中文](SDK_ENTRY_POINTS.zh-CN.md)

All SDKs use the same installed MCP/Runtime/browser. These are API layers, not separate engines. Choose one layer for a task; do not open the same environment through three clients.

## What actually exists

| Layer | Python | Node.js / TypeScript | Java | Go |
| --- | --- | --- | --- | --- |
| Quick browser entry | launch() | await launch() | KingAI.launch() | kingai.Launch(ctx, options, profileID) |
| Explicit client | KingAI | KingAI | KingAI | Client, returned by Connect |
| Browser session | BrowserSession | BrowserSession | KingAI.Session | Session |
| Agent action/state facade | BrowserAutomation | BrowserAutomation | No BrowserAutomation class yet | No BrowserAutomation type yet |

Python/Node expose three entry layers. Java/Go currently expose two; their generic client/session calls still access installed MCP tools. That is not the same as having the Agent facade's execute/get-current-state interface. Do not import a Java/Go BrowserAutomation that does not exist.

## 1. Quick entry: open an environment and operate pages

Use this for ordinary scripts. Defaults require the existing unique saved 默认环境; no temporary fallback is created. Installation and login are separate prerequisites.

Python:

```python
from kingai_browser import launch
with launch() as browser:
    browser.new_tab("https://example.com")
    print(browser.query(selector="a", limit=20))
```

Node.js:

```javascript
import { launch } from '@kingaibrowser/browser-api';
const browser = await launch();
try {
  await browser.newTab('https://example.com');
  console.log(await browser.query({ selector: 'a', limit: 20 }));
} finally { await browser.detach(); }
```

Java, inside an application method with KingAI and Map imported:

```java
try (KingAI.Session browser = KingAI.launch()) {
    browser.newTab("https://example.com");
    System.out.println(browser.query(Map.of("selector", "a", "limit", 20)));
}
```

Go, inside a function returning error with ctx and the kingai/fmt imports:

```go
browser, err := kingai.Launch(ctx, kingai.Options{}, "")
if err != nil { return err }
defer browser.Detach(ctx)
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
elements, err := browser.Query(ctx, kingai.Arguments{"selector": "a", "limit": 20})
if err != nil { return err }
fmt.Println(elements)
return nil
```

Explicit profile selection: Python launch(profile_id=id), Node launch({profileId:id}), Java KingAI.launch(options,id), Go Launch(ctx,options,id). The returned session owns the newly created client. Detaching releases that owned connection and keeps the browser.

## 2. Explicit client: profiles, tools and multiple sessions

Use this layer when creating/configuring profiles, choosing sessions, or controlling connection ownership. Creation does not launch a window; update closed profiles only.

| Task | Python | Node.js | Java | Go |
| --- | --- | --- | --- | --- |
| Construct/connect | with KingAI() as api | new KingAI(); await api.connect() | try (KingAI api = new KingAI()) | api,err := kingai.Connect(ctx,options) |
| Profile list | api.profiles() | await api.profiles() | api.profiles() | api.Profiles(ctx) |
| Create profile | api.create_profile(name) | await api.createProfile(name) | api.createProfile(name) | api.CreateProfile(ctx,name,nil) |
| Start selected profile | api.start(profile_id=id) | await api.start({profile_id:id}) | api.start(Map.of("profile_id",id)) | api.Start(ctx,Arguments{"profile_id":id}) |
| Discover/attach sessions | sessions / attach | sessions / attach | sessions / attach | Sessions / Attach |
| Generic invocation | call | call | call | Call |
| Release client | api.close() | await api.close() | api.close() | api.Close() |

A client close is not a browser-close request. Sessions returned by an explicit client's start do not own that external client; the caller cleans it up. See each language README for complete installation and configuration, and [API examples](API_EXAMPLES.md) for raw arguments and four-language generic calls.

## 3. Agent facade: action names and unified state

Use this for OpenManus-style adapters, not for every ordinary script. The facade contains no LLM or task planner. It maps action names to SDK calls, serializes observations and describes errors.

Python:

```python
import json
from kingai_browser import BrowserAutomation
with BrowserAutomation() as agent:
    agent.execute("go_to_url", url="https://example.com")
    state = agent.get_current_state()
    snapshot = json.loads(state["interactive_elements"])
    print(snapshot.get("elements", []))
```

Node.js:

```javascript
import { BrowserAutomation } from '@kingaibrowser/browser-api';
const agent = new BrowserAutomation();
try {
  await agent.execute('go_to_url', { url: 'https://example.com' });
  const state = await agent.getCurrentState();
  console.log(JSON.parse(state.interactive_elements).elements);
} finally { await agent.close(); }
```

interactive_elements is a JSON string containing a bounded snapshot, not a browser database field or live DOM object. Normal scripts use session.query/snapshot directly. The facade's state and operation observations help an external Agent assess outcomes; dispatch success is not business success.

Java/Go can build their adapter using session query/snapshot/read and generic calls, but the SDK does not currently package a matching BrowserAutomation facade for those languages. An Agent supporting stdio MCP can also connect directly without any language SDK; see [integration template](../examples/integrations/README.md).

## Lifecycle differences you must retain

| Operation | Result |
| --- | --- |
| Python with launch() exit | Detach owned session, release client, preserve window |
| Java automatic Session.close() | Detach owned session, release client, preserve window; non-owned cleanup is a no-op |
| Node/Go launch session detach/Detach | Detach, release owned client, preserve window |
| Python/Node BrowserAutomation.close | Release facade client, preserve window |
| Explicit browser shutdown | Python close_browser()/close(); Node closeBrowser()/close(); Java closeBrowser(); Go CloseBrowser()/Close() |

After releasing a connection, the old session cannot operate the retained window. Use Manager or discover/attach through a new authorized client. Java reports SESSION_DISCONNECTED when closeBrowser is attempted on a closed client. Never infer behavior from the name close without considering its object and language.

No entry bypasses login, humanize entitlement, concurrency limits, visibility or session ownership. The documentation change did not execute these examples or run builds/tests. [Detailed Python guide](../python/ENTRY_POINTS.md) · [Troubleshooting](../TROUBLESHOOTING.md).
