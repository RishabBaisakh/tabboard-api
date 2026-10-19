from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from goals.models import Goal
from tasks.models import Task


class TaskApiTests(TestCase):
    start = "2030-04-10T09:00:00Z"
    end = "2030-04-10T10:00:00Z"

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="task-user",
            email="task-user@example.com",
            password="Strong-password-123!",
        )
        self.other_user = user_model.objects.create_user(
            username="other-task-user",
            email="other-task-user@example.com",
            password="Strong-password-123!",
        )
        self.goal = Goal.objects.create(user=self.user, title="My goal")
        self.other_goal = Goal.objects.create(user=self.other_user, title="Other goal")
        self.client = self.client_for(self.user)

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        return client

    def payload(self, **overrides):
        payload = {
            "title": "Plan the day",
            "scheduled_start": self.start,
            "scheduled_end": self.end,
        }
        payload.update(overrides)
        return payload

    def test_create_scheduled_task(self):
        response = self.client.post(
            reverse("task-list"),
            self.payload(goal=self.goal.pk, description="Plan focus blocks"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.goal, self.goal)
        self.assertEqual(task.priority, Task.Priority.MEDIUM)
        self.assertEqual(task.status, Task.Status.TODO)
        self.assertIsNone(task.completed_at)

    def test_missing_schedule_is_rejected(self):
        for missing_field in ("scheduled_start", "scheduled_end"):
            with self.subTest(field=missing_field):
                payload = self.payload()
                payload.pop(missing_field)
                response = self.client.post(
                    reverse("task-list"), payload, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(missing_field, response.data)

    def test_end_must_be_after_start(self):
        for end in (self.start, "2030-04-10T08:59:59Z"):
            with self.subTest(end=end):
                response = self.client.post(
                    reverse("task-list"),
                    self.payload(scheduled_end=end),
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("scheduled_end", response.data)

    def test_naive_datetime_is_rejected(self):
        response = self.client.post(
            reverse("task-list"),
            self.payload(scheduled_start="2030-04-10T09:00:00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("scheduled_start", response.data)

    def test_list_retrieve_update_reschedule_and_delete(self):
        task = Task.objects.create(
            user=self.user,
            title="Existing",
            scheduled_start=datetime(2030, 4, 10, 9, tzinfo=timezone.utc),
            scheduled_end=datetime(2030, 4, 10, 10, tzinfo=timezone.utc),
        )
        list_response = self.client.get(reverse("task-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        detail_url = reverse("task-detail", args=[task.pk])
        retrieve_response = self.client.get(detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            detail_url,
            {
                "title": "Rescheduled",
                "scheduled_start": "2030-04-11T09:00:00Z",
                "scheduled_end": "2030-04-11T10:30:00Z",
            },
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Rescheduled")
        self.assertEqual(task.scheduled_start.isoformat(), "2030-04-11T09:00:00+00:00")

        put_response = self.client.put(
            detail_url,
            self.payload(title="Full update"),
            format="json",
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        invalid_put = self.client.put(
            detail_url,
            {"title": "Missing schedule"},
            format="json",
        )
        self.assertEqual(invalid_put.status_code, status.HTTP_400_BAD_REQUEST)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_task_user_is_derived_and_goal_must_belong_to_user(self):
        response = self.client.post(
            reverse("task-list"),
            self.payload(user=self.other_user.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.user, self.user)

        response = self.client.post(
            reverse("task-list"),
            self.payload(goal=self.other_goal.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("goal", response.data)

    def test_other_user_task_is_hidden_and_cannot_be_modified_or_deleted(self):
        task = Task.objects.create(
            user=self.other_user,
            title="Private",
            scheduled_start=datetime(2030, 4, 10, 9, tzinfo=timezone.utc),
            scheduled_end=datetime(2030, 4, 10, 10, tzinfo=timezone.utc),
        )
        detail_url = reverse("task-detail", args=[task.pk])
        self.assertEqual(
            self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            self.client.patch(
                detail_url, {"title": "Steal"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_authentication_is_required(self):
        client = APIClient()
        self.assertEqual(
            client.get(reverse("task-list")).status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            client.post(
                reverse("task-list"), self.payload(), format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_completion_timestamp_is_set_and_cleared_on_transitions(self):
        response = self.client.post(
            reverse("task-list"),
            self.payload(
                status=Task.Status.COMPLETED, completed_at="2000-01-01T00:00:00Z"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertIsNotNone(task.completed_at)
        self.assertNotEqual(task.completed_at.isoformat(), "2000-01-01T00:00:00+00:00")

        detail_url = reverse("task-detail", args=[task.pk])
        response = self.client.patch(
            detail_url,
            {"status": Task.Status.IN_PROGRESS},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

        response = self.client.patch(
            detail_url,
            {"status": Task.Status.COMPLETED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)

    def test_filters_and_ordering(self):
        earlier = Task.objects.create(
            user=self.user,
            title="Early high priority",
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
            goal=self.goal,
            scheduled_start=datetime(2030, 4, 10, 9, tzinfo=timezone.utc),
            scheduled_end=datetime(2030, 4, 10, 10, tzinfo=timezone.utc),
        )
        later = Task.objects.create(
            user=self.user,
            title="Later completed",
            status=Task.Status.COMPLETED,
            priority=Task.Priority.LOW,
            scheduled_start=datetime(2030, 4, 11, 9, tzinfo=timezone.utc),
            scheduled_end=datetime(2030, 4, 11, 10, tzinfo=timezone.utc),
        )
        response = self.client.get(reverse("task-list"))
        self.assertEqual(
            [item["id"] for item in response.data], [str(earlier.pk), str(later.pk)]
        )

        response = self.client.get(reverse("task-list") + "?status=completed")
        self.assertEqual([item["id"] for item in response.data], [str(later.pk)])
        response = self.client.get(reverse("task-list") + "?priority=high")
        self.assertEqual([item["id"] for item in response.data], [str(earlier.pk)])
        response = self.client.get(reverse("task-list") + f"?goal={self.goal.pk}")
        self.assertEqual([item["id"] for item in response.data], [str(earlier.pk)])
        response = self.client.get(
            reverse("task-list") + "?scheduled_start_after=2030-04-11T00:00:00Z"
        )
        self.assertEqual([item["id"] for item in response.data], [str(later.pk)])

    def test_deleting_goal_preserves_task_and_clears_goal(self):
        task = Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="Keep task",
            scheduled_start=datetime(2030, 4, 10, 9, tzinfo=timezone.utc),
            scheduled_end=datetime(2030, 4, 10, 10, tzinfo=timezone.utc),
        )
        self.goal.delete()
        task.refresh_from_db()
        self.assertIsNone(task.goal_id)


# Create your tests here.
