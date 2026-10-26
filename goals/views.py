from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from goals.models import Goal, GoalCategory


class GoalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalCategory
        fields = ("key", "name", "description")
        read_only_fields = fields


class GoalSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="key",
        queryset=GoalCategory.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Unknown or inactive category.",
            "invalid": "Invalid category key.",
        },
    )
    category_detail = GoalCategorySerializer(source="category", read_only=True)

    class Meta:
        model = Goal
        fields = (
            "id",
            "title",
            "description",
            "start_date",
            "due_date",
            "timeline",
            "motivation",
            "category",
            "category_detail",
        )
        read_only_fields = ("id",)


class GoalCategoryListView(ListAPIView):
    serializer_class = GoalCategorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return GoalCategory.objects.filter(is_active=True)


class UserGoalListView(ListCreateAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Goal.objects.filter(user=self.request.user).select_related(
            "category"
        )
        category_key = self.request.query_params.get("category")
        if category_key:
            if not GoalCategory.objects.filter(key=category_key).exists():
                raise ValidationError({"category": "Unknown category."})
            queryset = queryset.filter(category__key=category_key)
        return queryset.order_by("-created_at", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserGoalDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)
