from django.contrib import admin
from .models import WatchedSite, ChangeEvent

@admin.register(WatchedSite)
class WatchedSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "user", "check_frequency_minutes", "last_checked_at", "is_active")
    list_filter = ("is_active",)

@admin.register(ChangeEvent)
class ChangeEventAdmin(admin.ModelAdmin):
    list_display = ("site", "detected_at", "notified")
