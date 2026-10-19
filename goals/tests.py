from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from goals.models import Goal


class GoalListApiTests(TestCase):
    def test_goals_endpoint_lists_only_authenticated_users_goals(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="goal-owner",
            email="goal-owner@example.com",
            password="Strong-password-123!",
        )
        other_user = user_model.objects.create_user(
            username="other-goal-owner",
            email="other-goal-owner@example.com",
            password="Strong-password-123!",
        )
        own_goal = Goal.objects.create(user=user, title="Own goal")
        Goal.objects.create(user=other_user, title="Private goal")

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        response = client.get(reverse("goal-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own_goal.pk])
        self.assertIsNone(response.data[0]["due_date"])

    def test_goals_endpoint_requires_authentication(self):
        response = APIClient().get(reverse("goal-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_due_date_is_optional_and_future_dates_are_valid(self):
        user = get_user_model().objects.create_user(
            username="due-date-user",
            email="due-date-user@example.com",
            password="Strong-password-123!",
        )
        today = timezone.localdate()

        no_due_date = Goal.objects.create(user=user, title="No due date")
        future_goal = Goal(
            user=user,
            title="Future due date",
            due_date=today + timedelta(days=1),
        )
        future_goal.full_clean()
        future_goal.save()

        self.assertIsNone(no_due_date.due_date)
        self.assertEqual(future_goal.due_date, today + timedelta(days=1))

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        response = client.get(reverse("goal-list"))
        response_goals = {item["id"]: item for item in response.data}
        self.assertEqual(
            response_goals[future_goal.pk]["due_date"],
            (today + timedelta(days=1)).isoformat(),
        )

    def test_due_date_today_or_in_the_past_is_rejected(self):
        user = get_user_model().objects.create_user(
            username="invalid-due-date-user",
            email="invalid-due-date-user@example.com",
            password="Strong-password-123!",
        )
        today = timezone.localdate()
        for due_date in (today, today - timedelta(days=1)):
            with self.subTest(due_date=due_date):
                goal = Goal(
                    user=user,
                    title="Invalid due date",
                    due_date=due_date,
                )
                with self.assertRaises(ValidationError):
                    goal.full_clean()
