"""Ownership regression cases; not executed during this change."""
import unittest
from unittest.mock import Mock, patch
from kingai_browser import BrowserSession, launch


class LaunchOwnershipTests(unittest.TestCase):
    def test_cleanup_failure_does_not_replace_body_failure(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch()
        with patch.object(browser, "call", side_effect=RuntimeError("detach failed")):
            with self.assertRaisesRegex(ValueError, "body failure"):
                with browser:
                    raise ValueError("body failure")
        client.close.assert_called_once_with()

    def test_non_owned_context_does_not_close_browser_or_client(self):
        client = self.make_client()
        browser = BrowserSession(client, "external-session")
        with patch.object(browser, "call") as call:
            with browser:
                pass
        call.assert_not_called()
        client.close.assert_not_called()

    def test_owned_context_detaches_instead_of_closing_browser(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch()
        with patch.object(browser, "call", return_value={}) as call:
            with browser:
                pass
        call.assert_called_once_with("browser_detach")
        client.close.assert_called_once_with()

    def test_owned_context_detaches_after_body_failure(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch()
        with patch.object(browser, "call", return_value={}) as call:
            with self.assertRaisesRegex(ValueError, "body failure"):
                with browser:
                    raise ValueError("body failure")
        call.assert_called_once_with("browser_detach")

    def test_released_owned_context_does_not_detach_twice(self):
        client = self.make_client()
        browser = BrowserSession(client, "released-session")
        browser._owns_client = True
        client._closed = True
        with patch.object(browser, "call") as call:
            with browser:
                pass
        call.assert_not_called()

    def make_client(self):
        client = Mock()
        client._closed = False
        client.start.return_value = BrowserSession(client, "session-test")
        return client

    def test_launch_passes_profile_selection_without_creating_profiles(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch("saved-profile")
        client.start.assert_called_once_with("saved-profile", headless=False, temporary=False)
        client.create_profile.assert_not_called()
        self.assertTrue(browser._owns_client)

    def test_failed_start_releases_connection_without_retry(self):
        client = self.make_client()
        client.start.side_effect = RuntimeError("missing default")
        with patch("kingai_browser.KingAI", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "missing default"):
                launch()
        self.assertEqual(client.start.call_count, 1)
        client.close.assert_called_once_with()
        client.create_profile.assert_not_called()

    def test_detach_releases_connection_without_closing_browser(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch()
        # Use a real session; observe precisely which side effect was sent.
        with patch.object(browser, "call", return_value={}) as call:
            browser.detach()
        call.assert_called_once_with("browser_detach")
        client.close.assert_called_once_with()

    def test_close_releases_connection_even_if_browser_close_fails(self):
        client = self.make_client()
        with patch("kingai_browser.KingAI", return_value=client):
            browser = launch()
        with patch.object(browser, "call", side_effect=RuntimeError("unknown outcome")) as call:
            with self.assertRaisesRegex(RuntimeError, "unknown outcome"):
                browser.close()
        call.assert_called_once_with("browser_close")
        client.close.assert_called_once_with()
