from django.utils import timezone
from rest_framework import serializers

from goals.models import Goal
from tasks.models import Task


class AwareDateTimeField(serializers.DateTimeField):
    def enforce_timezone(self, value):
        if timezone.is_naive(value):
            raise serializers.ValidationError("Use a timezone-aware ISO-8601 datetime.")
        return super().enforce_timezone(value)


class TaskSerializer(serializers.ModelSerializer):
    scheduled_start = AwareDateTimeField()
    scheduled_end = AwareDateTimeField()
    goal = serializers.PrimaryKeyRelatedField(
        queryset=Goal.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "user",
            "title",
            "description",
            "status",
            "priority",
            "goal",
            "scheduled_start",
            "scheduled_end",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            fields["goal"].queryset = Goal.objects.filter(user=request.user)
        return fields

    def validate(self, attrs):
        start = attrs.get(
            "scheduled_start", getattr(self.instance, "scheduled_start", None)
        )
        end = attrs.get("scheduled_end", getattr(self.instance, "scheduled_end", None))
        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError(
                {"scheduled_end": "Must be later than scheduled_start."}
            )
        goal = attrs.get("goal")
        request = self.context.get("request")
        if goal is not None and request and goal.user_id != request.user.pk:
            raise serializers.ValidationError(
                {"goal": "Choose a goal owned by the authenticated user."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        if validated_data.get("status", Task.Status.TODO) == Task.Status.COMPLETED:
            validated_data["completed_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        previous_status = instance.status
        next_status = validated_data.get("status", previous_status)
        if (
            previous_status != Task.Status.COMPLETED
            and next_status == Task.Status.COMPLETED
        ):
            validated_data["completed_at"] = timezone.now()
        elif (
            previous_status == Task.Status.COMPLETED
            and next_status != Task.Status.COMPLETED
        ):
            validated_data["completed_at"] = None
        return super().update(instance, validated_data)
