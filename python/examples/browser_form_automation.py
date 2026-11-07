"""Create/configure a saved profile and submit a local form using observed DOM refs.

synchronous end-to-end example; no third-party form submission.
Prerequisite: serve examples/demo.html on port 8765, install the SDK and sign in.
Run from repository root: python python/examples/browser_form_automation.py --live
The new profile and browser window are retained after the example finishes.
"""
import argparse
import json
from uuid import uuid4

from kingai_browser import KingAI

URL = "http://127.0.0.1:8765/demo.html"


def one_ref(browser, selector):
    # The server returns observed DOM elements and opaque, session-bound refs.
    result = browser.query(selector=selector, include_html=True, limit=2)
    print("DOM query:", json.dumps(result, ensure_ascii=False))
    elements = result.get("elements", [])
    if len(elements) != 1 or not elements[0].get("ref"):
        raise RuntimeError(f"Expected exactly one actionable DOM element: {selector}")
    return elements[0]["ref"]


def run_workflow(api):
    print("Capabilities:", api.info())
    print("Saved environments:", api.profiles())

    # Create a fresh identity. Existing environments are not edited by this sample.
    name = "Python workflow " + uuid4().hex[:12]
    created = api.create_profile(name, language="en-US")
    profile_id = created["profileId"]
    # Settings must be saved BEFORE starting the environment.
    api.update_profile(profile_id, name=name + " configured")
    print("Configured environment:", api.profile(profile_id))

    browser = api.start(profile_id=profile_id)
    try:
        browser.new_tab(URL)
        browser.wait(selector="#demo-form", state="visible", timeout_ms=15000)
        print("Interactive DOM snapshot:", browser.snapshot(mode="interactive", limit=30))
        print("Bounded DOM inventory:", browser.query(limit=30, include_html=True, max_chars=12000))

        # Query again immediately before each action; do not invent or persist refs.
        browser.fill(ref=one_ref(browser, "#name"), text="KingAI Python", humanize=False)
        browser.fill(ref=one_ref(browser, "#message"), text="Hello from the Python SDK", humanize=False)
        browser.click(ref=one_ref(browser, "#submit"), humanize=False)
        # Dispatched != submitted: independently wait for a visible business result.
        browser.wait(selector='#result[data-submitted="true"]', text="Submitted: KingAI Python", timeout_ms=10000)
        result = browser.evaluate("document.querySelector('#result').textContent")
        expected = "Submitted: KingAI Python | Hello from the Python SDK"
        if result != expected:
            raise RuntimeError(f"Unexpected form result: {result!r}")
        print("Submission result:", result)
        print("Current page:", browser.read())
        print("Tabs:", browser.tabs())
        return {"profileId": profile_id, "result": result}
    finally:
        # Leave the saved identity and window available for inspection, even on error.
        browser.detach()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--executable")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to create and operate a real saved environment")
    with KingAI(args.executable) as api:
        print(run_workflow(api))
