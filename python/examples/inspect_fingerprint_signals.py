"""Inspect observable browser signals, not a universal anti-detection test.

Run with --live --profile-id SAVED_UUID. Reuses that profile, changes no settings.
The result describes this page context only; it does not predict site acceptance.
"""
import argparse
import json
from kingai_browser import launch

SIGNALS = """(() => {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl');
  const debug = gl && gl.getExtension('WEBGL_debug_renderer_info');
  return {
    url: location.href,
    webdriver: navigator.webdriver,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    languages: Array.from(navigator.languages),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory ?? null,
    screen: {width: screen.width, height: screen.height, colorDepth: screen.colorDepth},
    webgl: debug ? {
      vendor: gl.getParameter(debug.UNMASKED_VENDOR_WEBGL),
      renderer: gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)
    } : null
  };
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--profile-id", required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to inspect a real browser environment")
    with launch(profile_id=args.profile_id) as browser:
        browser.new_tab("https://example.com")
        browser.wait(selector="body", state="visible", timeout_ms=15000)
        # Read explicitly selected fields; do not dump the entire navigator/DOM.
        print(json.dumps(browser.evaluate_preview(SIGNALS), indent=2))
        print("Observed signals only. No anti-bot score or universal pass is asserted.")


if __name__ == "__main__":
    main()
