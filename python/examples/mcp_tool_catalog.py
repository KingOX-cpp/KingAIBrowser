"""Inspect every installed MCP tool and its authoritative input schema.

中文：只读接口目录；不打开浏览器，不执行目录中的工具。
English: read-only catalog, not a script that blindly executes every tool.
Run: python python/examples/mcp_tool_catalog.py --tool browser_query
Omit --tool to print all tool schemas. Requires compatible installed KingAI MCP.
"""
import argparse
import json
from kingai_browser import KingAI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", help="Exact tool name; omit to enumerate all tools")
    parser.add_argument("--executable", help="Absolute installed MCP executable path")
    args = parser.parse_args()
    with KingAI(args.executable) as api:
        # tools() handles server pagination; output includes required properties.
        # 不以某个 SDK 版本的固定工具清单代替当前安装版的 schema。
        tools = api.tools()
        selected = [item for item in tools if not args.tool or item["name"] == args.tool]
        if not selected:
            raise SystemExit("Tool not available in this installation: " + args.tool)
        for tool in selected:
            print("\n===", tool["name"], "===")
            print(tool.get("description", ""))
            print(json.dumps(tool.get("inputSchema", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
