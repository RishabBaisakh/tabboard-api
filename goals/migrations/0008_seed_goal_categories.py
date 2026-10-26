from django.db import migrations

# Single source of truth for the predefined life-area categories.
CATEGORIES = (
    (
        "health_wellness",
        "Health & Wellness",
        "Physical health, mental well-being, fitness, and healthy habits.",
    ),
    (
        "career_learning",
        "Career & Learning",
        "Career growth, education, professional skills, and personal development.",
    ),
    (
        "family_relationships",
        "Family & Relationships",
        "Family, friendships, romantic relationships, and social connections.",
    ),
    (
        "financial_life",
        "Financial Life",
        "Saving, budgeting, investing, debt management, and financial independence.",
    ),
    (
        "travel_experiences",
        "Travel & Experiences",
        "Trips, adventures, hobbies, and memorable experiences.",
    ),
    (
        "personal_life",
        "Personal Life",
        "Home, lifestyle, creativity, hobbies, and personal projects.",
    ),
)


def seed_categories(apps, schema_editor):
    GoalCategory = apps.get_model("goals", "GoalCategory")
    manager = GoalCategory.objects.using(schema_editor.connection.alias)
    # get_or_create keeps existing rows (and any admin edits) untouched on rerun.
    for key, name, description in CATEGORIES:
        manager.get_or_create(
            key=key, defaults={"name": name, "description": description}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0007_goalcategory_goal_category"),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
