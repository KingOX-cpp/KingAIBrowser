# Python entry points: launch, KingAI and BrowserAutomation

This is the Python-specific detailed guide. For the common architecture and actual Java/Go/Node capabilities, start with the [four-language overview](../docs/SDK_ENTRY_POINTS.md).

English | [简体中文](ENTRY_POINTS.zh-CN.md) | [Python guide](README.md) | [API recipes](../docs/API_EXAMPLES.md)

## 1. Choose an entry point

All three use the same installed MCP, Runtime and browser execution layer. They are not separate engines; do not create all three for one task.

| Entry | Object you receive | Purpose | Typical caller |
| --- | --- | --- | --- |
| `launch()` | BrowserSession | Discover/connect and start a saved environment in one entry | A normal page automation script |
| `KingAI` | Explicit client; start() returns sessions | Profile CRUD, tools, session discovery/attach and client ownership | Applications managing profiles or multiple sessions |
| `BrowserAutomation` | Agent action/state facade | Translate action names into SDK operations and assemble observations/errors | OpenManus BrowserUseTool and similar Agent adapters |

Use launch for a short script, KingAI for explicit environment/client management, and BrowserAutomation for an Agent action interface. BrowserAutomation contains no LLM or autonomous planner and grants no additional permissions.

## 2. Shared prerequisites

```shell
python -m pip install kingai-browser==0.3.3
python -m kingai_browser doctor
```

Install the browser, sign in and use compatible MCP/Runtime components. Discovery uses an explicit mcp_executable, KINGAI_MCP_EXECUTABLE or the Manager record. launch does not download software; the separate explicit install() entry is described in the [installation guide](../INSTALLATION.md).

Omitting profile_id selects the existing unique saved 默认环境. Missing/ambiguous defaults are errors, not temporary-profile fallbacks. If an environment is already open, inspect sessions and explicitly attach if authorized instead of blindly starting it again.

## 3. launch: operate a browser session directly

```python
from kingai_browser import launch

with launch() as browser:
    browser.new_tab("https://example.com")
    browser.wait(selector="body", state="visible", timeout_ms=15000)
    links = browser.query(selector="a", include_html=True, limit=20)
    for element in links.get("elements", []):
        print(element.get("ref"), element.get("name"))
    print(browser.read())
```

launch creates a KingAI client, starts the environment and returns a BrowserSession. Use new_tab, query, snapshot, click, fill and read on it. This example only reads links; it does not click or submit.

Explicit profile selection and connection settings:

```python
browser = launch(profile_id="actual-saved-profile-id", headless=False, timeout=60)
try:
    browser.new_tab("https://example.com")
    print(browser.snapshot(mode="interactive", limit=30))
finally:
    browser.detach()
```

Replace the profile ID with one returned by the profile list. timeout is a per-client-request timeout in seconds, not a total workflow duration. Temporary environments require explicit temporary=True; do not also select a saved identity.

Context exit detaches, releases the owned MCP connection and preserves the browser window. Explicit close_browser(), or its close() alias, closes the browser. You cannot operate the original session after releasing its connection.

## 4. KingAI: manage profiles and sessions explicitly

```python
from uuid import uuid4
from kingai_browser import KingAI

with KingAI() as api:
    print(api.profiles())
    created = api.create_profile("Example " + uuid4().hex[:12], language="en-US")
    profile_id = created["profileId"]
    api.update_profile(profile_id, name="Configured " + uuid4().hex[:12])
    print(api.profile(profile_id))
    browser = api.start(profile_id=profile_id)
    try:
        browser.new_tab("https://example.com")
        print(browser.query(selector="a", limit=20))
    finally:
        browser.detach()
```

This creates a real persistent profile and retains it. Repeated runs create more profiles. Update settings while the profile is closed. Deletion removes saved data and requires explicit confirmation; it is not routine finally cleanup.

Main client interfaces:

- profiles()/profile(id): saved environment summaries.
- create_profile/update_profile/delete_profile: saved profile management.
- start/sessions/attach: startup, active-session discovery and explicit attachment.
- tools()/call(name, arguments): available tool schemas and generic invocation.
- close(): disconnect this client's MCP, not an explicit browser-close request.

A client can manage multiple sessions. Serialize tab switching and input within a session. An api.start() session does not own the external client: browser.detach() leaves client cleanup to the outer with KingAI block.

For a retained session:

```python
with KingAI() as api:
    print(api.sessions())
    # Select an actual authorized session ID from the response.
    # browser = api.attach("actual-active-session-id")
    # print(browser.snapshot())
    # browser.detach()
```

profileId, sessionId, targetId and ref identify a saved profile, live session, tab and observed element respectively. They are not interchangeable.

## 5. BrowserAutomation: Agent actions and observations

```python
import json
from kingai_browser import BrowserAutomation

with BrowserAutomation() as agent_browser:
    operation = agent_browser.execute("go_to_url", url="https://example.com")
    state = agent_browser.get_current_state()
    print(state["url"], state["title"])
    snapshot = json.loads(state["interactive_elements"])
    for element in snapshot.get("elements", []):
        print(element.get("ref"), element.get("name"))
    links = agent_browser.execute("query", arguments={"selector": "a", "limit": 20})
    print(links)
```

The first page-requiring action starts or attaches a browser. Calling get_current_state immediately after construction raises a not-started error; execute go_to_url/open_tab first. Constructor options include either profile_id or session_id, plus headless and client connection options.

| Interface | Responsibility |
| --- | --- |
| execute(action, **arguments) | Execute actions such as go_to_url, click_element, input_text and query; the caller still chooses targets and plans tasks |
| get_current_state() | Read page, snapshot and tabs and assemble a new state dictionary |
| describe_error(error) | Describe structured errors and recovery hints; uncertain-connection errors can block subsequent actions to prevent duplicate side effects |
| close() / context exit | Disconnect the facade's client while preserving windows; this is not BrowserSession.close() |

interactive_elements is a **JSON string containing the entire bounded snapshot response**, created by the SDK, not a browser database field. Parse it with json.loads, then read elements. It is not a live DOM object or guaranteed complete HTML. The facade currently requests a compact snapshot; its historical field name does not mean every returned node is interactive.

Page-changing action receipts separate operationResult from observation/observationStatus and businessOutcome=not_verified. Observation failure does not replay preceding input. The Agent must inspect actual page results; actionDispatched alone is not business completion.

## 6. DOM and input: which interface?

Normal scripts call query()/snapshot() directly. Agent adapters use get_current_state() when they need the unified facade state.

```python
# On a page that actually contains this form input:
found = browser.query(selector="#name", limit=2)["elements"]
if len(found) != 1:
    raise RuntimeError("Expected one input")
browser.fill(ref=found[0]["ref"], text="KingAI", humanize=False)
```

This fragment needs a live session and a page containing #name; example.com does not contain that input. See the [local form examples](../examples/README.md). Observed elements are summaries: invoke SDK actions, not element.click() on a returned dictionary.

## 7. Lifecycle reference

| Object/action | Connection | Browser window |
| --- | --- | --- |
| Exit with launch() | Release owned client | Preserved |
| launch session detach() | Detach and release owned client | Preserved |
| launch session close_browser()/close() | Explicitly close, then release owned client | Closed |
| Exit with KingAI()/api.close() | Release client | Not explicitly closed |
| api.start() session detach() | Release session control; do not close external client | Preserved |
| Exit a non-owned session context | No automatic cleanup or takeover | Preserved |
| Exit with BrowserAutomation()/facade.close() | Release facade client | Preserved |

After release, the original object cannot continue operating the window. Use Manager or a new client with explicit authorized attach. Never steal SESSION_BUSY control, automatically reconnect or replay submissions after an uncertain outcome.

All entries retain account concurrency, Lease, humanize entitlement and page-visibility requirements. None exposes unrestricted raw CDP. AsyncKingAI is the async explicit-client interface, not a different browser engine.

This change documents behavior only; examples, builds, checks and tests were not executed. Native/browser behavior remains subject to installed capabilities and real-browser validation.
