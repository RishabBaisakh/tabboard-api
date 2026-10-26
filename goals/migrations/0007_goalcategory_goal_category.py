import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0006_goal_timeline_motivation"),
    ]

    operations = [
        migrations.CreateModel(
            name="GoalCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name_plural": "goal categories",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="goal",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="goals",
                to="goals.goalcategory",
            ),
        ),
    ]
