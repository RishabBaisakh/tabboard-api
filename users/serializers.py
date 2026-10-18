from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from users.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "display_name",
            "time_zone",
            "bio",
            "personality_tags",
            "current_interests",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate_time_zone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
            raise serializers.ValidationError(
                "Enter a valid IANA time zone identifier."
            ) from error
        return value

    def validate_personality_tags(self, value):
        if len(value) > 10:
            raise serializers.ValidationError(
                "A maximum of 10 personality tags is allowed."
            )
        return value

    def validate_current_interests(self, value):
        if len(value) > 10:
            raise serializers.ValidationError(
                "A maximum of 10 current interests is allowed."
            )
        return value
