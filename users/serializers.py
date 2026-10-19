from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers
from users.models import Interest, PersonalityTag, UserProfile
from users.services import update_user_profile


def validate_iana_time_zone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise serializers.ValidationError(
            "Enter a valid IANA time zone identifier."
        ) from error
    return value


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "display_name",
            "time_zone",
            "bio",
            "interests",
            "personality_tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "display_name",
            "created_at",
            "updated_at",
        )

    interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Interest.objects.filter(is_active=True),
        required=False,
    )
    personality_tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=PersonalityTag.objects.filter(is_active=True),
        required=False,
    )

    def validate_time_zone(self, value):
        return validate_iana_time_zone(value)

    def update(self, instance, validated_data):
        return update_user_profile(instance, validated_data)
