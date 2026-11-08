# Source installation and release status

## Prepared releases: Python 0.3.4 / Node.js 0.3.1

These source versions update registry descriptions and search keywords, align client version reporting, and include the existing installer progress implementations. Publication is pending account verification; the public versions remain Python 0.3.3 and Node.js 0.3.0 until the registries confirm otherwise.

Validation on 2026-11-08: 12 simulated Python installer tests passed; Python wheel/sdist build and Twine metadata checks passed; isolated Python installation, imports, CLI help and metadata checks passed. The Node tarball was installed in an isolated directory; its main exports, version and keywords passed checks, and invalid install arguments were rejected. No browser installer was downloaded or executed. This is not a real-browser compatibility test.

Python 0.3.3 adds stderr progress (size, percentage when known, speed, elapsed time and ETA), removes the ten-minute total download deadline, and adds --quiet / --network-timeout. Python and Node.js packages are now published on PyPI and npm. Java/Go progress implementations remain local source changes. This documentation update did not build or test any SDK.

## Python 0.3.2: system temporary downloads

The installer now defaults to the operating system's temporary directory on Windows and macOS. It does not require D:, a code/ directory or any developer-specific installation path. Downloads still open the native installer/DMG UI by default; the user chooses/completes installation. Version 0.3.1 used per-user storage and remains an immutable historical release. Java/Go/Node source defaults were aligned, without building or testing those languages in this change.

Python validation: 5 installer regression tests using fake download/process responses, source/wheel build, Twine metadata checks and isolated installation/import passed. No browser installer was downloaded or executed. Release caches and outputs remain under F:\kingai-pypi on the publisher's machine; this does not determine end-user defaults.

[English](README.md) · [中文](README.zh-CN.md) · [Samples/tests](SAMPLES.md)

SDK version: **0.3.0**. API contract: **1**. This repository publishes source code, not browser binaries or native MCP/Runtime components.

## Package status

| SDK | Source location | Package identity | Distribution status |
| --- | --- | --- | --- |
| Python | python/ | kingai-browser | PyPI 0.3.3 published on 2026-11-07; installer progress regressions and online CLI checks passed |
| Node.js / TypeScript | js/ | @kingaibrowser/browser-api | npm 0.3.0 published; online installation available |
| Java | java/ | cn.kingaibrowser.sdk:kingai-browser:0.3.0 | Local Maven install; no Maven Central release |
| Go | go/ | github.com/KingOX-cpp/KingAIBrowser/go | Local replace supported; no version tag claimed |

Public package names, namespace ownership, signing and publication credentials must be confirmed before registry release. Source on GitHub does not imply registry availability. For the nested Go module, a future tagged v0.3.0 module release requires the `go/v0.3.0` tag.

## Installation

Browser installers now have explicit four-language download entries; see [INSTALLATION.md](INSTALLATION.md) / [中文](INSTALLATION.zh-CN.md). Python packaging includes _kingai_installer.py; the Node files list includes installer.mjs; Java and Go include native installer helpers. These changes have not been built, installed, downloaded or tested in this task. Browser setup remains an interactive system operation; opening an installer is not proof of completion.

See the four language sections in either README. Keep download caches, temporary directories and build outputs on D: on Windows. For Maven, set both `maven.repo.local` and `kingai.build.directory`. For Go, set `GOMODCACHE`, `GOCACHE` and `GOTMPDIR`. Node installations should set `--cache`; Python installations should set pip's cache and `TEMP`/`TMP`.

Go dependencies include go.sum. Node's dependency range is declared in package.json; no application lockfile is distributed, so production applications should retain their resolved lockfiles. Java preview resources must stay in the JAR. Python's runtime uses only the standard library; source installation uses setuptools.

## Native compatibility

The SDK requires a compatible installed KingAI MCP and Runtime. `sdk_info` describes server-side API capabilities but is not proof that a running Runtime has been upgraded. Discover actual tools using `tools/list`. New profile CRUD tools are not added to an old native installation by installing this SDK.

This repository does not provide instructions to build private Chromium/Runtime sources. Obtain compatible native components through the browser distribution.

## Test evidence and remaining work

The original source SDK passed 17 tests against an in-memory MCP fixture on Windows on 2026-11-06. They cover minimal samples and selected SDK semantics. Public repository packaging, Go module-path changes, the js/ reorganization and new complete workflows have not been retested; package installation and real-browser behavior are not covered by that result.

Before a public package release, separately validate package contents/installability, runtime resource loading, supported operating systems, real MCP/Runtime compatibility, normal and abnormal process exit, account authorization and concurrency, humanize entitlement, page visibility, window-synchronization contention and browser input behavior. No compilation, build, check or test was run during this repository preparation task.
