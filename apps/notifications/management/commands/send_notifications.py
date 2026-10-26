from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.notifications.services import send_due_notifications


class Command(BaseCommand):
    help = "Dispatch scheduled email notifications (daily reminders and weekly summaries) to due users."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore 15-minute time window and day check, sending notifications immediately.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        force = options.get("force", False)
        self.stdout.write(f"Checking and sending notifications (force={force})...")
        counts = send_due_notifications(force=force)
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: {counts['total_sent']} notifications sent "
                f"({counts['daily_reminders_sent']} daily, {counts['weekly_summaries_sent']} weekly)."
            )
        )
