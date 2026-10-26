from decimal import Decimal
from django.db import migrations


def backfill_last_check_in_value(apps, schema_editor):
    Habit = apps.get_model('habits', 'Habit')
    Habit.objects.filter(last_check_in_date__isnull=False).update(
        last_check_in_value=Decimal('1.00')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0006_habit_last_check_in_value'),
    ]

    operations = [
        migrations.RunPython(backfill_last_check_in_value, reverse_code=migrations.RunPython.noop),
    ]
