from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from monitor.models import ChangeEvent, WatchedSite
from monitor.tasks import _hash_content, check_all_sites, check_site


class SiteCheckTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="test-password",
        )

    def make_site(self, **kwargs):
        defaults = {
            "user": self.user,
            "name": "Example",
            "url": "https://example.com",
            "css_selector": "",
            "check_frequency_minutes": 60,
            "is_active": True,
        }
        defaults.update(kwargs)
        return WatchedSite.objects.create(**defaults)

    @staticmethod
    def mock_response(html):
        response = Mock()
        response.text = html
        response.raise_for_status.return_value = None
        return response

    def test_first_check_stores_hash_without_creating_change_event(self):
        site = self.make_site()

        with patch(
            "monitor.tasks.requests.get",
            return_value=self.mock_response(
                "<html><body>Hello world</body></html>"
            ),
        ):
            result = check_site.run(site.id)

        site.refresh_from_db()

        self.assertEqual(result, "unchanged")
        self.assertEqual(
            site.last_hash,
            _hash_content("Hello world"),
        )
        self.assertIsNotNone(site.last_checked_at)
        self.assertEqual(
            ChangeEvent.objects.filter(site=site).count(),
            0,
        )

    def test_unchanged_content_does_not_create_event_or_send_email(self):
        site = self.make_site(
            last_hash=_hash_content("Same content"),
        )

        with patch(
            "monitor.tasks.requests.get",
            return_value=self.mock_response(
                "<html><body>Same content</body></html>"
            ),
        ):
            with patch(
                "monitor.tasks.send_mail"
            ) as mock_send_mail:
                result = check_site.run(site.id)

        self.assertEqual(result, "unchanged")
        self.assertEqual(
            ChangeEvent.objects.filter(site=site).count(),
            0,
        )
        mock_send_mail.assert_not_called()

    def test_changed_content_creates_event_and_sends_email(self):
        old_hash = _hash_content("Old content")

        site = self.make_site(
            last_hash=old_hash,
        )

        with patch(
            "monitor.tasks.requests.get",
            return_value=self.mock_response(
                "<html><body>New content</body></html>"
            ),
        ):
            with patch(
                "monitor.tasks.send_mail"
            ) as mock_send_mail:
                result = check_site.run(site.id)

        site.refresh_from_db()
        event = ChangeEvent.objects.get(site=site)

        self.assertEqual(result, "changed")
        self.assertEqual(event.old_hash, old_hash)
        self.assertEqual(
            event.new_hash,
            _hash_content("New content"),
        )
        self.assertTrue(event.notified)
        self.assertEqual(
            site.last_hash,
            _hash_content("New content"),
        )
        mock_send_mail.assert_called_once()

    def test_css_selector_ignores_changes_outside_selected_content(self):
        tracked_text = "Important content"

        site = self.make_site(
            css_selector="#tracked",
            last_hash=_hash_content(tracked_text),
        )

        html = """
        <html>
            <body>
                <div id="tracked">Important content</div>
                <div>Completely different noisy content</div>
            </body>
        </html>
        """

        with patch(
            "monitor.tasks.requests.get",
            return_value=self.mock_response(html),
        ):
            result = check_site.run(site.id)

        self.assertEqual(result, "unchanged")
        self.assertEqual(
            ChangeEvent.objects.filter(site=site).count(),
            0,
        )

    def test_inactive_site_is_not_fetched(self):
        site = self.make_site(
            is_active=False,
        )

        with patch(
            "monitor.tasks.requests.get"
        ) as mock_get:
            result = check_site.run(site.id)

        self.assertEqual(
            result,
            "site not found or inactive",
        )
        mock_get.assert_not_called()

    def test_fetch_failure_does_not_create_change_event(self):
        site = self.make_site()

        with patch(
            "monitor.tasks.requests.get",
            side_effect=requests.RequestException(
                "network unavailable"
            ),
        ):
            result = check_site.run(site.id)

        site.refresh_from_db()

        self.assertTrue(
            result.startswith("fetch failed:")
        )
        self.assertIsNone(site.last_checked_at)
        self.assertEqual(
            ChangeEvent.objects.filter(site=site).count(),
            0,
        )

    def test_scheduler_dispatches_only_due_active_sites(self):
        now = timezone.now()

        due_site = self.make_site(
            name="Due site",
            url="https://example.com/due",
            last_checked_at=None,
        )

        self.make_site(
            name="Not due",
            url="https://example.com/not-due",
            last_checked_at=now - timedelta(minutes=10),
            check_frequency_minutes=60,
        )

        self.make_site(
            name="Inactive",
            url="https://example.com/inactive",
            is_active=False,
        )

        with patch(
            "monitor.tasks.check_site.delay"
        ) as mock_delay:
            result = check_all_sites.run()

        self.assertEqual(
            result,
            "dispatched 1 site(s)",
        )
        mock_delay.assert_called_once_with(
            due_site.id
        )
