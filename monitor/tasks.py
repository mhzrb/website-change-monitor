import hashlib
import logging

import requests
from bs4 import BeautifulSoup
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import WatchedSite, ChangeEvent

logger = logging.getLogger(__name__)


def _extract_content(html: str, css_selector: str) -> str:
    """Pull out just the text we care about, so irrelevant noise
    (ads, timestamps, view counters) doesn't trigger false positives."""
    soup = BeautifulSoup(html, "html.parser")
    if css_selector:
        node = soup.select_one(css_selector)
        text = node.get_text(separator=" ", strip=True) if node else soup.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@shared_task
def check_site(site_id: int):
    """Fetch a single watched site, hash its content, and compare against
    the last known hash. If it changed, log a ChangeEvent and email the owner."""
    try:
        site = WatchedSite.objects.get(pk=site_id, is_active=True)
    except WatchedSite.DoesNotExist:
        return "site not found or inactive"

    try:
        response = requests.get(site.url, timeout=15, headers={"User-Agent": "SiteMonitorBot/1.0"})
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {site.url}: {e}")
        return f"fetch failed: {e}"

    content = _extract_content(response.text, site.css_selector)
    new_hash = _hash_content(content)
    old_hash = site.last_hash

    site.last_checked_at = timezone.now()

    if old_hash and old_hash != new_hash:
        event = ChangeEvent.objects.create(site=site, old_hash=old_hash, new_hash=new_hash)
        try:
            send_mail(
                subject=f"🔔 Change detected: {site.name}",
                message=f"The page you're watching changed:\n\n{site.name}\n{site.url}\n\nDetected at {event.detected_at}.",
                from_email=None,
                recipient_list=[site.user.email] if site.user.email else [],
            )
            event.notified = bool(site.user.email)
            event.save()
        except Exception as e:
            logger.warning(f"Failed to send email for {site.name}: {e}")

    site.last_hash = new_hash
    site.save()
    return "changed" if old_hash and old_hash != new_hash else "unchanged"


@shared_task
def check_all_sites():
    """Entry point for the periodic beat schedule (runs every few minutes).
    Only dispatches a real check for sites whose own check_frequency_minutes
    has actually elapsed, so a site set to "once a day" isn't hit every 15 min."""
    now = timezone.now()
    dispatched = 0
    for site in WatchedSite.objects.filter(is_active=True):
        due = (
            site.last_checked_at is None
            or (now - site.last_checked_at).total_seconds() >= site.check_frequency_minutes * 60
        )
        if due:
            check_site.delay(site.id)
            dispatched += 1
    return f"dispatched {dispatched} site(s)"
