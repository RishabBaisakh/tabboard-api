from django.db import migrations, models
from django.db.models.functions import TruncDate


def backfill_start_date(apps, schema_editor):
    Goal = apps.get_model("goals", "Goal")
    Goal.objects.using(schema_editor.connection.alias).filter(
        start_date__isnull=True
    ).update(start_date=TruncDate("created_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0003_goal_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="goal",
            name="start_date",
            field=models.DateField(null=True),
        ),
        migrations.RunPython(backfill_start_date, migrations.RunPython.noop),
    ]
