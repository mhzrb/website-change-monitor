from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
    help = "Creates (or updates) the periodic task that checks all watched sites every 15 minutes."

    def handle(self, *args, **options):
        schedule, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)
        task, created = PeriodicTask.objects.update_or_create(
            name="Check all watched sites",
            defaults={
                "interval": schedule,
                "task": "monitor.tasks.check_all_sites",
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} periodic task: {task.name} (every 15 min)"))
