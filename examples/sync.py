"""Shared sample entry point, exercised by unit tests using a fixture MCP."""
import argparse
from kingai_browser import KingAI

def run_sample(api, name="Python SDK 演示"):
    info = api.info()
    profiles = api.profiles()
    profile = api.create_profile(name)
    browser = api.start(profile_id=profile["profileId"])
    browser.new_tab("https://example.com")
    page = browser.read()
    preview = browser.evaluate_preview("({title:document.title,text:document.body.innerText})")
    browser.detach()
    return {"info": info, "profiles": profiles, "profileId": profile["profileId"], "page": page, "preview": preview}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Explicitly create an environment in your real installation")
    parser.add_argument("--executable")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to operate your real KingAI account/environment")
    with KingAI(args.executable) as api:
        print(run_sample(api))
