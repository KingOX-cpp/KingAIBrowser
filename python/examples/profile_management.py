"""Manage saved fingerprint environments without launching a browser.

list, create, inspect and configure a new profile; optional explicit deletion.
Run: python python/examples/profile_management.py --live
Requires a signed-in account and compatible installed MCP/Runtime.
"""
import argparse
import json
from uuid import uuid4
from kingai_browser import KingAI


def show(label, value):
    """Print JSON summaries, not full fingerprint configurations or credentials."""
    print(label)
    print(json.dumps(value, ensure_ascii=False, indent=2))


def manage_profiles(api, delete_created=False):
    # 1. Saved environment list. IDs come from the server; never guess them.
    # Profile lists contain summaries; the installed server defines their structure.
    show("Saved environments", api.profiles())
    show("API capabilities", api.info())

    # 2. Create a uniquely named saved environment. This does not open a window.
    # Create groups in the Manager before assigning them; this example uses the default group.
    name = "SDK profile example " + uuid4().hex[:12]
    created = api.create_profile(name, language="en-US")
    profile_id = created["profileId"]
    show("Created profile ID", created)

    # 3. Fetch one environment by its real ID.
    show("Profile summary", api.profile(profile_id))

    # 4. Update before startup. A running profile must be closed before editing.
    # Patch objects merge recursively; do not log complete configurations or secrets.
    api.update_profile(
        profile_id,
        name=name + " configured",
        patch={"locale": {"language": "en-US", "accept_languages": "en-US,en"}},
    )
    show("Updated summary", api.profile(profile_id))

    # 5. No automatic deletion. Only this example's newly created profile is eligible.
    # Deletion removes persistent data; never clean up an existing user profile implicitly.
    if delete_created:
        show("Explicit deletion", api.delete_profile(profile_id, confirm=True))
    else:
        print("Retained saved profile:", profile_id)
    return profile_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow real profile changes")
    parser.add_argument("--delete-created", action="store_true", help="Delete ONLY the profile created by this run")
    parser.add_argument("--executable", help="Absolute installed MCP path")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live to change saved environments")
    with KingAI(args.executable) as api:
        manage_profiles(api, args.delete_created)


if __name__ == "__main__":
    main()
