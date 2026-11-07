"""Keep multiple saved environments open under one account's concurrency limit.

Repeat --profile-id for each DISTINCT saved UUID. Starts are intentionally
sequential; the windows then coexist. No concurrent input targets one shared tab.
Run: python python/examples/open_multiple_environments.py --live
     --profile-id UUID_A --profile-id UUID_B
"""
import argparse
from kingai_browser import KingAI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--profile-id", action="append", required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to open real saved environments")
    if len(set(args.profile_id)) != len(args.profile_id):
        parser.error("Profile IDs must be distinct")
    opened = []
    with KingAI() as api:
        try:
            for profile_id in args.profile_id:
                browser = api.start(profile_id=profile_id)
                opened.append(browser)
                print("Opened environment:", profile_id, "session:", browser.session_id)
                browser.new_tab("https://example.com")
            print("All requested environments are now open:", len(opened))
        finally:
            # A later limit/start error must not close already-open user windows.
            # No automatic retry, account-limit bypass or profile deletion occurs.
            for browser in opened:
                try:
                    browser.detach()
                except Exception as error:
                    print("Detach failed for session:", browser.session_id, str(error))


if __name__ == "__main__":
    main()
