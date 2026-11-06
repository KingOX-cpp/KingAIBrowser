import asyncio
import importlib.util
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor

from kingai_browser import KingAI, KingAIError, AsyncKingAI

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sample_sync", ROOT / "examples/sync.py")
sample = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample)
async_spec = importlib.util.spec_from_file_location("sample_async", ROOT / "examples/async.py")
async_sample = importlib.util.module_from_spec(async_spec)
async_spec.loader.exec_module(async_sample)
FIXTURE = os.environ.get("KINGAI_TEST_MCP")

@unittest.skipUnless(FIXTURE, "Set KINGAI_TEST_MCP to the test-only fixture executable")
class SampleTests(unittest.TestCase):
    def setUp(self):
        self.api = KingAI(FIXTURE, timeout=3)
        self.addCleanup(self.api.close)

    def test_real_sample_uses_stdio_sdk(self):
        result = sample.run_sample(self.api, "sample")
        self.assertEqual(result["page"]["url"], "https://example.com")
        self.assertEqual(result["page"]["title"], "Example Domain")
        self.assertFalse(result["preview"]["truncated"])
        trace = self.api.call("fixture_trace")
        self.assertEqual(trace.count("browser_start"), 1)
        self.assertEqual(trace.count("tabs_new"), 1)
        self.assertEqual(trace.count("browser_evaluate"), 1)
        self.assertIn("browser_detach", trace)
        self.assertNotIn("browser_close", trace)

    def test_crud_confirmation_and_busy(self):
        profile = self.api.create_profile("crud")["profileId"]
        self.api.update_profile(profile, name="renamed")
        self.assertEqual(self.api.profile(profile)["name"], "renamed")
        with self.assertRaises(KingAIError) as caught:
            self.api.delete_profile(profile)
        self.assertEqual(caught.exception.code, "CONFIRMATION_REQUIRED")
        browser = self.api.start(profile)
        with self.assertRaises(KingAIError) as caught:
            self.api.update_profile(profile, name="busy")
        self.assertEqual(caught.exception.code, "SESSION_BUSY")
        browser.close()
        self.assertTrue(self.api.delete_profile(profile, confirm=True)["deleted"])

    def test_observe_and_no_error_retry(self):
        browser = self.api.start()
        result = browser.click(ref="e1", observe=True)
        self.assertEqual(result["operationStatus"], "dispatched")
        self.assertEqual(result["observationStatus"], "captured")
        self.api.call("fixture_fail_next", {"code": "RESULT_TOO_LARGE"})
        with self.assertRaises(KingAIError) as caught:
            browser.evaluate("document.title")
        self.assertEqual(caught.exception.code, "RESULT_TOO_LARGE")
        self.assertEqual(self.api.call("fixture_trace").count("browser_evaluate"), 1)

    def test_bad_text_is_not_a_timeout(self):
        with self.assertRaises(KingAIError) as caught:
            self.api.call("fixture_bad_response")
        self.assertEqual(caught.exception.code, "INVALID_TOOL_RESPONSE")

    def test_observation_groups_do_not_interleave(self):
        browser = self.api.start()
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls = [pool.submit(browser.click, ref="e1", observe=True) for _ in range(2)]
            for call in calls:
                self.assertEqual(call.result()["observationStatus"], "captured")
        trace = [name for name in self.api.call("fixture_trace") if name in {"browser_click", "browser_read", "browser_snapshot", "tabs_list"}]
        self.assertEqual(trace, ["browser_click", "browser_read", "browser_snapshot", "tabs_list"] * 2)

@unittest.skipUnless(FIXTURE, "Test-only fixture executable required")
class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_sample_flow(self):
        async with AsyncKingAI(FIXTURE, timeout=3) as api:
            self.assertEqual((await async_sample.run_sample(api))["url"], "https://example.com")

    async def test_cancellation_does_not_repeat_request(self):
        async with AsyncKingAI(FIXTURE, timeout=3) as api:
            task = asyncio.create_task(api.call("fixture_delay"))
            await asyncio.sleep(.05)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual((await api.call("fixture_trace")).count("fixture_delay"), 1)

if __name__ == "__main__":
    unittest.main()
