from collections.abc import Mapping

from rest_framework import serializers

from users.serializers import validate_iana_time_zone


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                names = ", ".join(sorted(unknown_fields))
                raise serializers.ValidationError(
                    {"non_field_errors": [f"Unexpected field(s): {names}."]}
                )
        return super().to_internal_value(data)


class QuestionAnswerSerializer(StrictSerializer):
    question_key = serializers.SlugField(max_length=80, required=False)
    question_id = serializers.IntegerField(required=False, min_value=1)
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )

    def validate(self, attrs):
        has_key = "question_key" in attrs
        has_id = "question_id" in attrs
        if has_key == has_id:
            raise serializers.ValidationError(
                "Provide exactly one of question_key or question_id."
            )
        option_ids = attrs["selected_option_ids"]
        if len(option_ids) != len(set(option_ids)):
            raise serializers.ValidationError(
                {"selected_option_ids": "Duplicate option IDs are not allowed."}
            )
        return attrs


class BasicInfoStepSerializer(StrictSerializer):
    display_name = serializers.CharField(
        max_length=80, required=False, allow_blank=True
    )
    bio = serializers.CharField(max_length=300, required=False, allow_blank=True)
    time_zone = serializers.CharField(max_length=50, required=False)
    answers = QuestionAnswerSerializer(many=True, required=False)

    def validate_time_zone(self, value):
        return validate_iana_time_zone(value)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide profile fields or question answers."
            )
        identities = [
            (
                ("key", answer["question_key"])
                if "question_key" in answer
                else ("id", answer["question_id"])
            )
            for answer in attrs.get("answers", [])
        ]
        if len(identities) != len(set(identities)):
            raise serializers.ValidationError(
                {"answers": "A question may only be submitted once per request."}
            )
        return attrs


class ProfileOptionStepSerializer(StrictSerializer):
    selected_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_selected_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate option IDs are not allowed.")
        return value


class OnboardingPatchSerializer(serializers.Serializer):
    STEP_SERIALIZERS = {
        "basic_info": BasicInfoStepSerializer,
        "interests": ProfileOptionStepSerializer,
        "personality_tags": ProfileOptionStepSerializer,
    }

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Expected a JSON object.")
        step = data.get("step")
        if not isinstance(step, str):
            raise serializers.ValidationError(
                {"step": "Use basic_info, interests, or personality_tags."}
            )
        serializer_class = self.STEP_SERIALIZERS.get(step)
        if serializer_class is None:
            raise serializers.ValidationError(
                {"step": "Use basic_info, interests, or personality_tags."}
            )

        payload = {key: value for key, value in data.items() if key != "step"}
        serializer = serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return {"step": step, "data": serializer.validated_data}
