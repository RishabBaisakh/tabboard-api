from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ("id", "title", "due_date")
        read_only_fields = fields


class UserGoalListView(ListAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).order_by("id")
