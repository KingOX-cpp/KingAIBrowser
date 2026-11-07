# 浏览器下载与安装

[English](INSTALLATION.md) | 简体中文

Python、Node.js、Java、Go 均使用各自语言的下载实现；Java/Go/Node 不依赖 Python。只有显式调用安装接口才会下载，import、doctor、路径定位和 launch 不会静默下载软件。

| 平台 | 支持范围 | 官方下载地址 |
| --- | --- | --- |
| Windows | 仅 Intel/AMD 64 位 x64；不支持 32 位 Windows、Windows ARM | https://161.118.255.111/download/KingAIBrowserSetup.exe |
| macOS | 仅 Apple 芯片；不支持 Intel Mac | https://161.118.255.111/download/KingAIBrowser.dmg |

Apple 芯片上的 Rosetta 进程会尝试识别实际硬件。Linux 不适用这两个安装包。

## “自动安装”具体做什么

接口会自动下载，并可启动 Windows 安装向导或打开 Mac DMG。**目前不是静默、无人值守安装**：请在系统界面中完成安装或 DMG 拖放步骤。没有猜测安装器参数，不自动提权、不覆盖已有应用、不绕过 Gatekeeper。安装后打开 Manager 并登录，让管理器登记 MCP 路径，再运行 doctor。

下载目录不等于浏览器安装目录。Windows 默认下载到 `D:\code\KingAIBrowser-downloads`，Mac 默认到 `~/Downloads/KingAIBrowser`，每次下载创建独立子目录。失败会移除本次未完成的文件，不覆盖之前的安装包或浏览器用户数据；完整安装包不自动删除。

返回状态：

- `downloaded`：文件已下载，未打开安装器。
- `installer_started`：系统接受了启动安装器/打开 DMG 的请求，不代表安装成功、MCP/Runtime 已就绪。
- Python 的 `existing_installation`：已有路径登记能找到 MCP 及同目录 Runtime，因此复用。只说明文件存在，不证明版本兼容或已登录。`reuse_existing=False` 强制下载；仅下载模式始终下载。

## Python

```powershell
python -m kingai_browser install --download-dir D:\code\KingAIBrowser-downloads
python -m kingai_browser install --download-only
python -m kingai_browser install --no-reuse-existing
```

```python
from kingai_browser import install

result = install(download_dir=r"D:\code\KingAIBrowser-downloads", download_only=True)
print(result["status"], result["installerPath"])
```

`download_only=False` 会打开安装器；`sha256` 可传独立可信来源提供的预期校验值。Mac 上省略 Windows 路径，或使用 Mac 的绝对路径。

## Node.js / TypeScript

```powershell
node js/cli.mjs install --download-only --download-dir D:\code\KingAIBrowser-downloads
```

```javascript
import { install } from '@kingai/browser-api';
const result = await install({ downloadOnly: true });
console.log(result.status, result.installerPath);
```

参数为 `downloadDir`、`downloadOnly`、`sha256`；`downloadOnly` 默认 false，会打开安装器。

## Java

```java
import cn.kingaibrowser.sdk.BrowserInstaller;
import cn.kingaibrowser.sdk.KingAI;

// Inside a method handling IOException and InterruptedException.
BrowserInstaller.Result result = KingAI.install(null, true, null);
System.out.println(result.status() + ": " + result.installerPath());
// BrowserInstaller.openInstaller(result);
```

`KingAI.install(downloadDir, downloadOnly, expectedSha256)` 第一个参数是绝对 Path，null 使用平台默认目录。只下载可用 `BrowserInstaller.download`；之后可显式调用 `openInstaller`。请妥善保管文件，避免在不可信目录中被替换。

## Go

```go
// Inside a function returning error, with ctx, kingai and fmt available.
result, err := kingai.Install(ctx, kingai.InstallOptions{DownloadOnly: true})
if err != nil { return err }
fmt.Println(result.Status, result.InstallerPath)
return nil
```

选项为 `DownloadDir`、`DownloadOnly`、`SHA256`。`DownloadOnly` 默认 false，会打开安装器。下载完成但打开失败时，可从同时返回的 result 中取得文件路径。

## HTTPS 与文件校验

保持证书与主机名校验。IP 下载地址的证书必须可信且覆盖这个 IP；如证书自签名、过期或地址不匹配，下载明确失败，不提供跳过 TLS 校验的选项。HTTPS 跳转到 HTTP 会被拒绝。

拒绝 HTML 错误页面、空文件、长度不符和超过 3 GiB 的下载；Windows 文件还检查 MZ 可执行文件头。返回实际 SHA-256；如果调用方提供了可信预期 SHA-256，还会比对，不一致则不启动安装器。**只计算哈希不等于验证来源**，只有与调用方提供的值匹配时 `checksumVerified` 才为 true。目前没有获得这两个安装包的可信固定哈希，因此源码没有编造哈希。

下载目录应由当前用户信任和控制。本接口不宣称已验证发布者数字签名。系统权限、安全提示、账号登录及会员权益规则继续适用。

## 验证与发布状态

Python SDK 0.3.0 已于 2026-11-07 发布到 PyPI。源码包与 wheel 构建、Twine 元数据检查、独立本地安装与导入、公开文件 SHA-256 比对，以及从 PyPI 全新在线安装与导入均通过；缓存与产物保存在 F:\kingai-pypi。浏览器安装包未下载或执行，安装流程和下载服务器证书仍未验证；Java/Go/Node 安装器未在此次 Python 发布中构建或测试。
