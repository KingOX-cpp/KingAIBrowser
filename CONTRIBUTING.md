# Contributing

Use [GitHub Issues](https://github.com/KingOX-cpp/KingAIBrowser/issues) for SDK bugs and feature requests. Include language/runtime version, SDK version, installed KingAI MCP version, tool name, error code and a minimal reproduction. Remove credentials, cookies, account details and private page content.

## Scope

This repository hosts client SDKs, documentation, examples and a test-only MCP simulator. Browser engine patches, Manager, Runtime and production account services are distributed separately. Do not include profile databases, browser user data, binaries or credentials in contributions.

## SDK changes

Keep raw MCP argument names and server result fields unchanged. Preserve structured errors. Do not automatically retry browser side effects after timeout or observation failure. New convenience methods should delegate to installed tools, not duplicate fingerprint or entitlement logic. Keep preview resource files with their Java/Go packages.

## Samples and testing

Use reusable sample functions so tests and command-line examples exercise the same implementation. The fixture only simulates tool behavior; a passing fixture test is not a native/browser compatibility claim. See [SAMPLES.md](SAMPLES.md) for explicit test commands and scope. Live examples require `--live` and can modify real saved profiles.

For Windows development, keep cloned dependencies, caches and build outputs on D:. Do not run compilation, builds, checks or tests on a maintainer's workspace without authorization. No Chromium/GN or Rust build is needed to edit these SDKs.

When submitting a change, state what changed, tests actually run (or explicitly not run), and whether any real-browser behavior remains unverified. Contributions must preserve applicable third-party notices and be compatible with the repository's MIT license.
