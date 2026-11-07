# Browser download and installation

[English](INSTALLATION.md) | [简体中文](INSTALLATION.zh-CN.md)

All four SDKs download the same official installers using their own language runtime. Java/Go/Node do not invoke Python. This is an explicit install action: import, doctor, discovery and launch do not silently download software.

| Platform | Support | Official installer |
| --- | --- | --- |
| Windows | Intel/AMD x64 only; not 32-bit Windows or Windows ARM | https://161.118.255.111/download/KingAIBrowserSetup.exe |
| macOS | Apple Silicon only; not Intel Mac | https://161.118.255.111/download/KingAIBrowser.dmg |

Rosetta processes on Apple Silicon are detected where possible. The architecture check describes the host platform, not just the Python/JVM process bitness. Linux is unsupported by these installers.

## Installation semantics

The SDK downloads the file and can open the Windows installation wizard or the macOS DMG. **This is not an unattended/silent installation.** Complete the wizard or DMG installation steps yourself. No unsupported silent flags, administrator elevation, automatic application replacement or Gatekeeper bypass are used. After installation, open Manager and sign in so it can register the installed MCP path, then run doctor.

`downloadDir` means installer storage, **not** the browser installation directory. Windows defaults to `D:\code\KingAIBrowser-downloads`; macOS defaults to `~/Downloads/KingAIBrowser`. Each download has a unique subdirectory. Partial files are removed on failure; previous installers and browser data are not overwritten. The SDK does not delete completed installers automatically.

Statuses are deliberately limited:

- `downloaded`: the file finished downloading; no installer was opened.
- `installer_started`: the operating-system launcher accepted the request. This does not confirm a successful installation or ready MCP/Runtime.
- Python-only `existing_installation`: normal discovery already found an MCP with its sibling Runtime. This is a filesystem check, not proof of native compatibility or login. Set `reuse_existing=False` to download anyway; download-only always downloads.

## Python

```powershell
# After installing the local Python SDK:
python -m kingai_browser install --download-dir D:\code\KingAIBrowser-downloads
# Download without opening the installer:
python -m kingai_browser install --download-only
# Force a new download even if an existing installation is found:
python -m kingai_browser install --no-reuse-existing
```

```python
from kingai_browser import install

result = install(download_dir=r"D:\code\KingAIBrowser-downloads", download_only=True)
print(result["status"], result["installerPath"])
# To download/open the installer UI explicitly: install(reuse_existing=False)
```

On macOS omit the Windows directory or pass an absolute macOS download path.

## Node.js / TypeScript

```powershell
node js/cli.mjs install --download-dir D:\code\KingAIBrowser-downloads --download-only
```

```javascript
import { install } from '@kingai/browser-api';
const result = await install({ downloadOnly: true });
console.log(result.status, result.installerPath);
// downloadOnly:false (default) also opens the native installer UI.
```

## Java

```java
import cn.kingaibrowser.sdk.BrowserInstaller;
import cn.kingaibrowser.sdk.KingAI;

// Function-body snippet; caller handles IOException/InterruptedException.
BrowserInstaller.Result result = KingAI.install(null, true, null);
System.out.println(result.status() + ": " + result.installerPath());
// Optional second explicit step:
// BrowserInstaller.openInstaller(result);
```

`KingAI.install(downloadDir, downloadOnly, expectedSha256)` accepts an absolute Path or null for the platform default. `BrowserInstaller.download` is the download-only primitive. Keep the returned installer at a trusted path before opening it.

## Go

```go
// Function-body snippet; ctx is context.Context, import kingai and fmt.
result, err := kingai.Install(ctx, kingai.InstallOptions{DownloadOnly: true})
if err != nil { return err }
fmt.Println(result.Status, result.InstallerPath)
return nil
```

Options: `DownloadDir`, `DownloadOnly`, `SHA256`. `DownloadOnly:false` also opens the native installer UI. If opening fails after download, Go returns the downloaded result alongside the error so the file can be located.

## HTTPS and checksums

HTTPS certificate and hostname verification remain enabled. An IP-based URL must have a valid trusted certificate covering that IP. If these URLs have a mismatched/self-signed/untrusted certificate, installation fails; use a properly certified download endpoint rather than disabling TLS validation. Redirects to HTTP are rejected. Error-page HTML, empty/truncated downloads and files larger than 3 GiB are rejected; Windows payloads must have an MZ executable header.

Every result includes the calculated SHA-256. An independently obtained trusted expected checksum can be passed as Python `sha256`, Node `sha256`, Java `expectedSha256`, Go `SHA256`, or CLI `--sha256`. **A calculated hash alone is not an authenticity verification.** `checksumVerified` is true only when a supplied expected checksum matches. No expected checksums were supplied for these URLs, so none are invented or embedded.

Never run downloaded files from an untrusted/writable-by-others directory. These helpers do not claim publisher-signature validation. OS installation permissions, security prompts, browser login and account entitlement remain applicable.

## Validation status

Python SDK 0.3.0 was published to PyPI on 2026-11-07. Source/wheel build, Twine metadata checks, isolated local installation/import, public artifact SHA-256 comparison and clean installation/import from PyPI passed. Release caches and outputs are under F:\kingai-pypi. Browser installers were not downloaded or executed; platform installation and download-certificate availability remain unverified. Java/Go/Node installers have not been built or tested in this publication task.
