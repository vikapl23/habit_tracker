from django.core.management.base import BaseCommand

from apps.habits.models import Habit
from apps.habits.services.streaks import recalculate_habit_streaks


class Command(BaseCommand):
    help = "Recalculate current_streak, longest_streak, and last_check_in_date for habits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--habit-id",
            type=int,
            dest="habit_id",
            help="Recalculate only for a specific habit ID.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            dest="user_id",
            help="Recalculate only for habits belonging to a specific user ID.",
        )

    def handle(self, *args, **options):
        qs = Habit.objects.select_related("user").all()
        if options.get("habit_id"):
            qs = qs.filter(id=options["habit_id"])
        if options.get("user_id"):
            qs = qs.filter(user_id=options["user_id"])

        count = 0
        for habit in qs.iterator():
            recalculate_habit_streaks(habit)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully recalculated streaks for {count} habit(s).")
        )
