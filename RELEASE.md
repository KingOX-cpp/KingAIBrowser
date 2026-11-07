# Source installation and release status

[English](README.md) · [中文](README.zh-CN.md) · [Samples/tests](SAMPLES.md)

SDK version: **0.3.0**. API contract: **1**. This repository publishes source code, not browser binaries or native MCP/Runtime components.

## Package status

| SDK | Source location | Package identity | Distribution status |
| --- | --- | --- | --- |
| Python | python/ | kingai-browser | PyPI 0.3.0 published on 2026-11-07; online install/import verified |
| Node.js / TypeScript | js/ | @kingai/browser-api | Local package install; no npm release |
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
