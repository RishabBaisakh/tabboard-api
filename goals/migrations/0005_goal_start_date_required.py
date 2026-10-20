import django.utils.timezone
from django.db import migrations, models


# Separate from 0004: PostgreSQL rejects ALTER TABLE after row updates in one transaction.
class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0004_goal_start_date_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="goal",
            name="start_date",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
