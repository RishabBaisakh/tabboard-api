import hashlib

from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


def copy_legacy_profile_options(apps, schema_editor):
    UserProfile = apps.get_model("users", "UserProfile")
    Interest = apps.get_model("users", "Interest")
    PersonalityTag = apps.get_model("users", "PersonalityTag")
    database = schema_editor.connection.alias

    def get_option(model, value):
        name = value.strip()
        if not name:
            return None
        key = slugify(name)[:50].strip("-")
        if not key:
            key = "legacy-" + hashlib.sha256(name.encode()).hexdigest()[:16]
        base_key = key
        suffix = 1
        while model.objects.using(database).filter(key=key).exclude(name=name).exists():
            suffix_text = f"-{suffix}"
            key = f"{base_key[:50 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        option, _ = model.objects.using(database).get_or_create(
            key=key,
            defaults={"name": name, "is_active": True},
        )
        return option

    profiles = UserProfile.objects.using(database).all().iterator()
    for profile in profiles:
        for value in profile.legacy_current_interests or []:
            option = get_option(Interest, value)
            if option:
                profile.interests.add(option)
        for value in profile.legacy_personality_tags or []:
            option = get_option(PersonalityTag, value)
            if option:
                profile.personality_tags.add(option)

    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    for user in User.objects.using(database).iterator():
        UserProfile.objects.using(database).get_or_create(user_id=user.pk)


def restore_legacy_profile_options(apps, schema_editor):
    UserProfile = apps.get_model("users", "UserProfile")
    database = schema_editor.connection.alias
    for profile in UserProfile.objects.using(database).all().iterator():
        profile.legacy_current_interests = list(
            profile.interests.values_list("name", flat=True)
        )
        profile.legacy_personality_tags = list(
            profile.personality_tags.values_list("name", flat=True)
        )
        profile.save(
            using=database,
            update_fields=["legacy_current_interests", "legacy_personality_tags"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_interest_personalitytag"),
    ]

    operations = [
        migrations.RenameField(
            model_name="userprofile",
            old_name="current_interests",
            new_name="legacy_current_interests",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="interests",
            field=models.ManyToManyField(
                blank=True, related_name="profiles", to="users.interest"
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name="userprofile",
            old_name="personality_tags",
            new_name="legacy_personality_tags",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="personality_tags",
            field=models.ManyToManyField(
                blank=True, related_name="profiles", to="users.personalitytag"
            ),
        ),
        migrations.RunPython(
            copy_legacy_profile_options,
            restore_legacy_profile_options,
        ),
    ]
