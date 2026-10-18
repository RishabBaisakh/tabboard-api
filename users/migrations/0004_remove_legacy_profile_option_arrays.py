from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_remove_userprofile_current_interests_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="legacy_current_interests",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="legacy_personality_tags",
        ),
    ]
