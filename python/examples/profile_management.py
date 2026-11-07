"""Manage saved fingerprint environments without launching a browser.

中文：列出、创建、读取、修改环境；只有显式 --delete-created 才删除本次新建的环境。
English: list, create, inspect and configure a new profile; optional explicit deletion.
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
    # 环境列表返回摘要；具体结构以已安装服务器为准。
    show("Saved environments / 已保存环境", api.profiles())
    show("API capabilities / 接口能力", api.info())

    # 2. Create a uniquely named saved environment. This does not open a window.
    # 分组如需填写，必须先在管理器中创建；这里保留默认分组。
    name = "SDK profile example " + uuid4().hex[:12]
    created = api.create_profile(name, language="en-US")
    profile_id = created["profileId"]
    show("Created profile ID / 新环境 ID", created)

    # 3. Fetch one environment by its real ID.
    show("Profile summary / 环境摘要", api.profile(profile_id))

    # 4. Update before startup. A running profile must be closed before editing.
    # patch 是递归合并，不要把完整配置或秘密打印出来。
    api.update_profile(
        profile_id,
        name=name + " configured",
        patch={"locale": {"language": "en-US", "accept_languages": "en-US,en"}},
    )
    show("Updated summary / 修改后摘要", api.profile(profile_id))

    # 5. No automatic deletion. Only this example's newly created profile is eligible.
    # 删除会移除持久数据；不对传入的已有环境执行清理。
    if delete_created:
        show("Explicit deletion / 显式删除", api.delete_profile(profile_id, confirm=True))
    else:
        print("Retained saved profile / 已保留环境:", profile_id)
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
