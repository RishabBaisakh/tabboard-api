from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = ("id",)


class UserGoalListView(ListCreateAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).order_by(
            "-created_at", "-id"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserGoalDetailView(RetrieveUpdateAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)
