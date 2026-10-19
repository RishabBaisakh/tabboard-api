from django.db import transaction

from users.models import UserProfile


def get_or_create_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@transaction.atomic
def update_user_profile(profile, data):
    values = dict(data)
    changed_fields = []

    for field in ("bio", "time_zone"):
        if field in values:
            setattr(profile, field, values.pop(field))
            changed_fields.append(field)

    if changed_fields:
        profile.save(update_fields=[*changed_fields, "updated_at"])

    for field in ("interests", "personality_tags"):
        if field in values:
            getattr(profile, field).set(values[field])

    return profile
