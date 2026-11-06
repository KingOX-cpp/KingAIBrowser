import asyncio
from kingai_browser import AsyncKingAI

async def run_sample(api):
    browser = await api.start()  # unique existing 默认环境
    await browser.new_tab("https://example.com")
    page = await browser.read()
    await browser.detach()
    return page

async def main():
    import sys
    if "--live" not in sys.argv:
        raise SystemExit("Pass --live to operate your real KingAI environment")
    async with AsyncKingAI() as api:
        print(await run_sample(api))

if __name__ == "__main__":
    asyncio.run(main())
