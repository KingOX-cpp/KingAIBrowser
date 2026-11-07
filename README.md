<div align="center">
  <img src="images/new-logo.png" width="80" alt="KingAI Browser" />
  <h1>KingAI Browser</h1>
  <p><strong>Isolated fingerprint environments. AI agents that operate your browser.</strong></p>
  <p>Python · Node.js / TypeScript · Java · Go · Agent MCP</p>
  <p><a href="README.zh-CN.md">简体中文</a> | English | <a href="https://www.kingaibrowser.cn/">Official Website & Download</a> | <a href="https://kingaibrowser.ccwu.cc/">Alternative Website</a> | <a href="https://www.kingaibrowser.cn/help/en/">Help</a></p>
</div>

KingAI Browser combines persistent fingerprint profiles, Chromium/Blink source-level modifications and browser-native automation. AI agents use its **stdio MCP server**; applications use the **four SDKs in this repository**. Both paths share the installed MCP, Runtime and browser execution layer.

**SDK 0.3.0 · MIT License · No Playwright dependency · No HTTP service required**

This repository contains open-source client SDKs, samples and tests. Download KingAI Browser from the [official website](https://www.kingaibrowser.cn/), [alternative website](https://kingaibrowser.ccwu.cc/) or [GitHub Releases](https://github.com/KingOX-cpp/KingAIBrowser/releases). Python SDK 0.3.3 is [published on PyPI](https://pypi.org/project/kingai-browser/0.3.3/): `python -m pip install kingai-browser`. The Node.js SDK is also available on [npm](https://www.npmjs.com/package/@kingaibrowser/browser-api); Maven publication is still pending.

## Install online

Both Python and Node.js SDKs are published. You do not need to clone this repository to install them.

Python:

```shell
pip install kingai-browser
python -m kingai_browser install
```

Node.js / TypeScript (run both commands in your application directory):

```shell
npm install @kingaibrowser/browser-api
npx kingai-browser install
```

The first command installs the SDK; the second explicitly downloads and opens the browser installer. Installers use the system temporary directory by default; finish the installation UI yourself, then open Manager and sign in. An existing installation may be reused. Browser installation is not a silent process. Node.js requires version 22 or newer. Run npx in the project where you installed the package so it resolves the local kingai-browser command.

[PyPI package](https://pypi.org/project/kingai-browser/) · [npm package](https://www.npmjs.com/package/@kingaibrowser/browser-api) · [Full installation guide](INSTALLATION.md)

## Download the browser installer

Supports Windows Intel/AMD x64 and Apple Silicon macOS only, not Windows ARM, 32-bit Windows or Intel Mac. Each language has a native downloader. Explicit install calls can download and open the installer/DMG; finish its UI steps yourself. This is not silent installation.

```powershell
python -m kingai_browser install --download-only
# Download and open the installer UI
python -m kingai_browser install
```

```python
from kingai_browser import install
result = install(download_only=True)
print(result["status"], result["installerPath"])
```

Installer downloads default to the system temporary directory on Windows and macOS. The download directory is not the browser installation directory. TLS verification stays enabled; invalid/mismatched IP certificates fail. Supply a trusted SHA-256 to verify the payload. After installation, open Manager, sign in and run doctor. No installer was downloaded or executed, and no build/check/test was run in this change.

[Full installation guide](INSTALLATION.md)

## Six core features

KingAI Browser combines everyday web tools, isolated fingerprint environments and AI workflows. These six features follow the product website's feature overview.

| Feature | Description | Highlights |
| --- | --- | --- |
| **01 · Web video recording** | Hover over a supported player to start or stop recording. Controls follow the player without covering its picture; recordings are saved locally with the output path shown. | Native HTML `<video>` capture, automatic finalization when tabs close, asynchronous file writes in a separate process. |
| **02 · Web text enhancements** | Explicit shortcuts help select, copy and access native menus for actual DOM text when page scripts interfere. | `Shift + right-click` for the native menu, `Alt + C` to copy the selection, `Alt + drag` for temporary text selection. |
| **03 · Permanently free fingerprint manager** | Create, edit, group and launch saved environments, each with separate User Data, cookies, proxy settings and configuration. | No environment-count or launch-count limit for everyday management; isolated profile data and identity configuration with per-profile proxies. |
| **04 · Source-level fingerprint patches + humanize** | Handle fingerprint surfaces inside Chromium/Blink and naturalize automation in the browser input layer. | Stable Canvas / Audio / ClientRects noise, real WebGL / WebGPU hardware templates, natural mouse trajectories, typing rhythm and continuous scrolling. |
| **05 · Window synchronization** | Drive multiple browser windows from one controller while each retains its own fingerprint, cookies and proxy. | Mouse, keyboard, scrolling, Chinese text input, address-bar paste, tabs, multi-monitor support and grid layouts. |
| **06 · AI automation** | Record actions as reusable Skills, use the built-in Agent to help adapt to page/element changes, or connect an external Agent through MCP. | Skill recording/playback, step debugging, element reselection, Agent MCP integration and four language SDKs. |

Free fingerprint management covers everyday profile management and manual launches. Window synchronization, humanize, Skills and MCP concurrency follow account entitlements. Recording requires a supported HTML video player; text enhancements operate on actual DOM text, not OCR of images or Canvas content.

## DETECTION MATRIX

The following reproduces the website's comparison and browser implementation descriptions. The Chrome + Playwright column describes its reference configuration, not a fixed property of every Playwright setup.

| Detection surface | Chrome + Playwright (website reference setup) | KingAI Browser | Implementation |
| --- | --- | --- | --- |
| reCAPTCHA v3 | **0.1 · bot** | **0.9 · human** | Server-verified result in a specific test environment. |
| `navigator.webdriver` | `true` | `false` | Chromium / Blink source-level patches. |
| UA / Client Hints | Browser-engine defaults | Consistent per-profile configuration | Cross-check UA, brand, version and platform. |
| CDP Error stack detection | Can trigger detection hooks | Prevents detection side effects | V8 Inspector protection. |
| Mouse-down signals | buttons / pressure often default to 0 | **buttons 1 · pressure 0.5** | Explicit browser input handling; values here describe left-button press. |
| Mouse movement and clicks | Straight lines or fixed coordinates | Bézier curves and natural timing | Browser-layer humanize. |
| Humanized typing | Text entered in one batch | Timing, mistakes and correction | Browser-layer humanize. |
| Fingerprint configuration consistency | Requires manual assembly and maintenance | Validation across configuration surfaces | Source-level patches and startup validation. |

**The website's 0.1 / 0.9 comparison was measured under specific configuration, network and test conditions. It is not an SDK test result or a guarantee of acceptance by any website, anti-fraud system or CAPTCHA.** Proxy quality, account history and actual behavior affect results; humanize requires valid account entitlement.

![KingAI fingerprint environment manager](images/manager-dashboard.png)

Lifecycle update: Python launch contexts and Java automatic Session resource cleanup detach and preserve windows. Explicit browser shutdown uses Python close()/close_browser(), Node close()/closeBrowser(), Java closeBrowser(), or Go Close()/CloseBrowser(). New ownership cases and launch/doctor changes are unexecuted; the historical 17-test result does not cover them.

After disconnecting, the original Session can no longer operate the retained window. Close it in Manager, or discover the real active session through a new client and explicitly attach if authorized. No automatic reconnection occurs. Java closeBrowser() throws SESSION_DISCONNECTED if its client is closed.

## Quick entry and diagnostics

Start with the [four-language entry-point guide](docs/SDK_ENTRY_POINTS.md): launch, explicit client and Agent facade capabilities, examples and lifecycle differences. Python/Node provide BrowserAutomation; Java/Go currently provide clients and sessions without that facade. [中文](docs/SDK_ENTRY_POINTS.zh-CN.md).

Choose the right Python entry: [launch, KingAI and BrowserAutomation explained](python/ENTRY_POINTS.md), with complete usage examples and lifecycle rules. [中文](python/ENTRY_POINTS.zh-CN.md).

```python
from kingai_browser import launch

with launch() as browser:
    browser.new_tab("https://example.com")
    print(browser.read())
```

Install the browser and sign in first. launch uses the existing unique default profile; context exit detaches and preserves the browser. See each SDK guide for its entry and explicit profile selection.

```powershell
python -m kingai_browser doctor
node js/cli.mjs doctor
```

[Troubleshooting / 故障排查](TROUBLESHOOTING.md). The new entries and diagnostics have not been executed or validated in this change.

## Fingerprint environments + AI automation

| Capability | What it provides |
| --- | --- |
| Persistent fingerprint profiles | Each UUID profile has its own browser data, cookies, cache, proxy configuration and fingerprint noise key. Reuse a saved identity across sessions. |
| Chromium / Blink modifications | Engine-level handling of UA / Client Hints, Canvas, Audio, ClientRects, fonts, WebRTC, WebGL / WebGPU and hardware-related surfaces. |
| Configuration consistency | Coordinates language, timezone, proxy region and hardware/graphics information, with startup validation of conflicting settings. |
| Browser-native humanize | Mouse trajectories, keyboard timing and scrolling in the browser input layer, including button/pressure handling. Requires account entitlement. |
| Agent MCP | Open profiles, inspect pages, click, type, navigate, manage tabs and exchange structured results through stdio MCP. |
| Reusable Skills | Record workflows in the browser; agents discover parameters, start playback, query status or cancel through MCP. |
| Four SDKs | Python, Node.js/TypeScript, Java and Go invoke the same MCP tools. |

The browser also includes multi-window synchronization and Skill debugging. Availability follows the installed version and account entitlement. See [browser technology](BROWSER_TECHNOLOGY.md).

## Automation signals and CDP detection

KingAI addresses automation detection inside Chromium/Blink and the browser input layer, including `navigator.webdriver` and button/pressure data in automated mouse events. Agents connect through **managed MCP tools** without requesting a DevTools port or debugger WebSocket URL.

The SDK does not expose unrestricted raw CDP or require Playwright/Puppeteer. Internal execution can still use protected Chromium interfaces; stdio alone does not remove automation signals. These modifications aim to reduce detectable automation differences, **not guarantee acceptance by every site**. IP reputation, account history, behavior and changing website rules also matter.

## Architecture

```text
AI agent ──────────────────────────┐
                                  ▼
Python / Node.js / Java / Go → installed KingAI MCP (stdio)
                                  │ authenticated IPC
                                  ▼
                              KingAI Runtime
                                  │
                                  ▼
                    KingAI Browser + saved profile
```

Each SDK owns its MCP child-process connection. No SDK HTTP daemon is needed. Runtime manages browser execution and account/profile access. Complete fingerprint configurations stay in the browser system.

## Before you start

1. Install KingAI Browser and sign in through its Manager. MCP/Runtime must support the tools required by SDK 0.3.0; SDK installation alone does not upgrade them.
2. Locate **KingAIMcpServer.exe**, with **KingAIRuntime.exe** beside it. The main browser executable is not the MCP server.
3. Set the path below, or use the installation record written by a compatible Manager. The Manager need not stay open just for path discovery.

```powershell
# Replace the example path with your installed MCP executable.
$env:KINGAI_MCP_EXECUTABLE = 'D:\Apps\KingAIBrowser\KingAIMcpServer.exe'
git clone https://github.com/KingOX-cpp/KingAIBrowser.git D:\code\KingAIBrowser
cd D:\code\KingAIBrowser
```

Discovery: explicit SDK option → `KINGAI_MCP_EXECUTABLE` → per-user Manager record. Discovery/launch do not scan disks or download a browser; use the explicit install entry above when needed. The sample runner targets Windows; other platform paths in the SDK are not proof of tested browser availability.

## Complete automation examples

Start with [complete workflows](examples/README.md): environment listing, creation and settings → DOM observation → element queries → input → click → submission-result confirmation. A shared local form is included, so these samples do not depend on a third-party website.

| Python | Node.js | Java | Go |
| --- | --- | --- | --- |
| [browser_form_automation.py](python/examples/browser_form_automation.py) | [browser_form_automation.mjs](js/examples/browser_form_automation.mjs) | [Workflow.java](java/src/main/java/cn/kingaibrowser/sdk/samples/Workflow.java) | [main.go](go/examples/workflow/main.go) |

SDK code is organized by language in `python/`, `js/`, `java/` and `go/`. `examples/` contains the shared playground and example guide. The snippets below are minimal entry points; use the workflows above for complete interaction examples.

## Python

Python 3.10+; runtime library uses only the standard library.

```powershell
New-Item -ItemType Directory -Force D:\code\kingai-sdk-temp | Out-Null
$env:TEMP = 'D:\code\kingai-sdk-temp'
$env:TMP = $env:TEMP
python -m pip install --cache-dir D:\code\kingai-sdk-cache\pip .\python
python .\python\examples\browser_form_automation.py --live
```

```python
from kingai_browser import KingAI

with KingAI() as api:
    print(api.profiles())
    profile = api.create_profile("My Python profile")
    browser = api.start(profile_id=profile["profileId"])
    browser.new_tab("https://example.com")
    print(browser.read())
    browser.detach()
```

Also includes `AsyncKingAI` and the `BrowserAutomation` agent facade. [Python docs](python/README.md) · [profile management](python/examples/profile_management.py) · [async form automation](python/examples/async_browser_form_automation.py).

## Node.js / TypeScript

Node.js 22+. Install from npm in your application directory, then download/open the browser installer:

```powershell
npm install @kingaibrowser/browser-api
npx kingai-browser install
```

```javascript
import { KingAI } from '@kingaibrowser/browser-api';

const api = new KingAI();
try {
  console.log(await api.profiles());
  const profile = await api.createProfile('My Node profile');
  const browser = await api.start({ profile_id: profile.profileId });
  await browser.newTab('https://example.com');
  console.log(await browser.read());
  await browser.detach();
} finally { await api.close(); }
```

TypeScript declarations are included. To run the [repository sample](js/examples/saved_profile_quickstart.mjs), install dependencies in js/ with `npm install --cache D:\code\kingai-sdk-cache\npm`, then run `node examples/saved_profile_quickstart.mjs --live` from js/.

## Java

Java 17+ and Maven; uses Jackson and connects directly over stdio.

```powershell
mvn -f java/pom.xml -Dmaven.repo.local=D:/code/kingai-sdk-cache/m2 -Dkingai.build.directory=D:/code/kingai-sdk-build/java install
```

Your application can then depend on local Maven artifact `cn.kingaibrowser.sdk:kingai-browser:0.3.0`, using the same local repository path. This is not a Maven Central release.

```java
import cn.kingaibrowser.sdk.KingAI;

try (KingAI api = new KingAI()) {
    System.out.println(api.profiles());
    KingAI.Session browser = api.start(); // Existing saved 默认环境
    browser.newTab("https://example.com");
    System.out.println(browser.read());
    browser.detach();
}
```

[Java docs](java/README.md) · [full profile-creation sample](java/src/main/java/cn/kingaibrowser/sdk/samples/Sample.java).

## Go

Go 1.24+. In your application's `go.mod`, use the local checkout:

```go
require github.com/KingOX-cpp/KingAIBrowser/go v0.0.0
replace github.com/KingOX-cpp/KingAIBrowser/go => D:/code/KingAIBrowser/go
```

`v0.0.0` is a local-replace placeholder, not a published release tag. Import `kingai "github.com/KingOX-cpp/KingAIBrowser/go"` and call:

```go
api, err := kingai.Connect(ctx, kingai.Options{})
if err != nil { return err }
defer api.Close()
browser, err := api.Start(ctx, nil) // Existing saved 默认环境
if err != nil { return err }
if _, err = browser.NewTab(ctx, "https://example.com"); err != nil { return err }
page, err := browser.Read(ctx)
if err != nil { return err }
fmt.Println(page)
_, err = browser.Detach(ctx)
return err
```

The snippet is a function body with `context` and `fmt` imported by the caller. Set `GOMODCACHE`, `GOCACHE`, `GOTMPDIR` to D: before resolving dependencies. [Go docs](go/README.md) · [runnable sample](go/examples/basic/main.go). From `go/`, run `go run ./examples/basic --live`.

## Connect an AI agent through MCP

Use **Agent integration** in the Manager to install MCP into a supported agent. For a client with manual stdio configuration, adapt this to its configuration format:

```json
{
  "mcpServers": {
    "kingai-browser": {
      "command": "D:\\Apps\\KingAIBrowser\\KingAIMcpServer.exe",
      "args": []
    }
  }
}
```

Replace the path. The agent must support MCP stdio and accept the server connection. `tools/list` provides the authoritative schemas. Supported server versions provide Skill tools: `skills_list`, `skill_describe`, `skill_run`, `skill_status`, `skill_cancel`.

Example prompt: “Open my saved Research profile, visit example.com and read the page. Keep the browser open when finished.”

![Agent integration in KingAI Manager](images/mcp-skill-run.png)

## Samples and tests

The earlier minimal samples and fixture tests call the same reusable functions. The new complete workflows are separate live examples and have not been tested in this task. Real CLI use requires `--live`; saved-profile samples detach and leave windows open. The minimal samples can return duplicate-name errors; complete workflows generate unique environment names. The minimal async sample uses the existing default profile.

The source SDK's previous Windows run passed **17 fixture-backed tests**: Python 7, Node.js 4, Java 3, Go 3. These exercise SDK stdio communication with an in-memory MCP simulator, sample sequences, selected CRUD errors, no automatic replay, observation locking and preview bounds. **This public-repository layout and updated Go module path have not been retested.** These tests do not validate real browsing, fingerprint detection or account entitlements.

See [sample/test details](SAMPLES.md). With Python, Node.js, Java, Maven and Go installed:

```powershell
.\tests\Run-Samples.ps1 -GoExecutable go -MavenCommand mvn.cmd
```

The runner keeps dependencies/outputs on D: and does not build Chromium or Rust. Tests do not fall back to a real browser when the test MCP path is absent.

## API behavior to know

- `tools` / `Tools` and `call` / `Call` expose available MCP tools. Raw arguments remain snake_case; returned IDs include `sessionId` and `targetId`.
- `start()` without a profile selects the existing unique **默认环境**. It does not create a missing default. Temporary profiles require an explicit request.
- Client close disconnects its MCP. Explicit session close methods close browsers. Profile CRUD requires a compatible installed MCP/Runtime and login.
- Account limits apply to concurrently open environments, not clicks or SDK calls. Humanize requires a valid entitlement; requested flags/metadata alone do not prove it was applied.
- Input may require a visible selected page. For `PAGE_NOT_VISIBLE`, restore the window and activate the intended tab.
- Sessions use selected tabs; serialize multi-step workflows. These are not Playwright-compatible multi-Page objects.
- Timeout/disconnection does not prove an action failed. Side effects are not automatically retried. Use explicit preview methods for bounded evaluation results.

[API contract](CONTRACT.md) · [source installation / release notes](RELEASE.md) · [GitHub Issues](https://github.com/KingOX-cpp/KingAIBrowser/issues). Remove secrets and account data from reports.

## License

The Python, Node.js, Java and Go SDKs, samples and tests are available under the [MIT License](LICENSE). You may use, copy, modify, redistribute and use them commercially while retaining the copyright and license notice. Applicable third-party notices are preserved in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt). This repository does not vendor CloakBrowser code.

## Websites and browser downloads

- Official website: **https://www.kingaibrowser.cn/**
- Alternative website: **https://kingaibrowser.ccwu.cc/**
- Browser downloads on GitHub Releases: **https://github.com/KingOX-cpp/KingAIBrowser/releases**
