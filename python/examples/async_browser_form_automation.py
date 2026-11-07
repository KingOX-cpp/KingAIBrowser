"""Async profile creation, DOM inspection, input and submission confirmation.

sequential async workflow, not concurrent actions on one selected tab.
Prerequisite: serve examples/demo.html on http://127.0.0.1:8765 first.
Run: python python/examples/async_browser_form_automation.py --live
"""
import argparse
import asyncio
from uuid import uuid4
from kingai_browser import AsyncKingAI


async def one_ref(browser, selector):
    """Return a fresh unique observed ref; never reuse refs from another page."""
    observed = await browser.query(selector=selector, include_html=True, limit=2)
    print("DOM:", observed)
    elements = observed.get("elements", [])
    if len(elements) != 1 or not elements[0].get("ref"):
        raise RuntimeError("Expected one actionable element: " + selector)
    return elements[0]["ref"]


async def run_form(api):
    # Read saved environments before creating anything. No existing profile is edited.
    print("Saved environments:", await api.profiles())
    name = "Async SDK form " + uuid4().hex[:12]
    created = await api.create_profile(name, language="en-US")
    profile_id = created["profileId"]
    await api.update_profile(profile_id, name=name + " configured")
    print("Configured:", await api.profile(profile_id))

    browser = await api.start(profile_id=profile_id)
    try:
        await browser.new_tab("http://127.0.0.1:8765/demo.html")
        # Wait for an explicit condition rather than assuming navigation is ready.
        await browser.wait(selector="#demo-form", state="visible", timeout_ms=15000)
        print("Snapshot:", await browser.snapshot(mode="interactive", limit=30))

        # Sequential awaits keep input tied to the selected tab.
        # humanize=False only disables humanize; it does not bypass account access.
        name_ref = await one_ref(browser, "#name")
        await browser.fill(ref=name_ref, text="KingAI Async", humanize=False)
        message_ref = await one_ref(browser, "#message")
        await browser.fill(ref=message_ref, text="Hello from async Python", humanize=False)
        button_ref = await one_ref(browser, "#submit")
        await browser.click(ref=button_ref, humanize=False)

        # Independently confirm business state after the click was dispatched.
        await browser.wait(selector='#result[data-submitted="true"]', timeout_ms=10000)
        result = await browser.evaluate("document.querySelector('#result').textContent")
        if result != "Submitted: KingAI Async | Hello from async Python":
            raise RuntimeError("Unexpected form result: " + repr(result))
        print("Confirmed result:", result)
        print("Current tabs:", await browser.tabs())
        return {"profileId": profile_id, "result": result}
    finally:
        # Do not close/delete the environment as an implicit cleanup side effect.
        await browser.detach()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--executable", help="Absolute installed MCP path")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live to create and operate a real saved environment")
    # Cancelled awaits do not undo already-dispatched browser actions.
    async with AsyncKingAI(args.executable) as api:
        print(await run_form(api))


if __name__ == "__main__":
    asyncio.run(main())
