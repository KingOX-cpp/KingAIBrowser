"""Reuse a saved profile's cookies and login state without exporting secrets.

Run with --live --profile-id SAVED_UUID --url https://your-site.example.
Sign in manually in this profile first. Reopening a profile preserves its data,
but an expired or server-revoked login is not renewed automatically.
"""
import argparse
from kingai_browser import launch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to open an existing saved environment")
    # No profile creation, fingerprint reset, cookie import or login automation.
    with launch(profile_id=args.profile_id) as browser:
        browser.new_tab(args.url)
        print("Opened saved profile:", args.profile_id)
        print("Current page:", browser.read())
        print("Inspect the window to confirm the site's actual login state.")
        # Context exit detaches and releases MCP, preserving the window and data.


if __name__ == "__main__":
    main()
