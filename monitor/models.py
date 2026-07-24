from django.contrib.auth.models import User
from django.db import models


class WatchedSite(models.Model):
    FREQUENCY_CHOICES = [
        (15, "Every 15 minutes"),
        (60, "Every hour"),
        (360, "Every 6 hours"),
        (1440, "Once a day"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watched_sites")
    name = models.CharField(max_length=200)
    url = models.URLField()
    css_selector = models.CharField(
        max_length=200, blank=True,
        help_text="Optional CSS selector to watch only part of the page, e.g. '#content'. Leave blank to watch the whole page.",
    )
    check_frequency_minutes = models.PositiveIntegerField(choices=FREQUENCY_CHOICES, default=60)
    last_hash = models.CharField(max_length=64, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.url})"


class ChangeEvent(models.Model):
    """Logged every time a watched site's content hash changes."""
    site = models.ForeignKey(WatchedSite, on_delete=models.CASCADE, related_name="changes")
    detected_at = models.DateTimeField(auto_now_add=True)
    old_hash = models.CharField(max_length=64, blank=True)
    new_hash = models.CharField(max_length=64)
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Change on {self.site.name} at {self.detected_at}"
