from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from goals.models import Goal, GoalCategory


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
        newest_goal = Goal.objects.create(user=user, title="Newest goal")
        Goal.objects.create(user=other_user, title="Private goal")

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        response = client.get(reverse("goal-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data], [newest_goal.pk, own_goal.pk]
        )
        self.assertIsNone(response.data[1]["due_date"])

    def test_goals_endpoint_requires_authentication(self):
        response = APIClient().get(reverse("goal-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_create_goal_with_optional_due_date(self):
        user = get_user_model().objects.create_user(
            username="goal-creator",
            email="goal-creator@example.com",
            password="Strong-password-123!",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

        response = client.post(
            reverse("goal-list"),
            {
                "title": "Learn Rust and build projects",
                "description": "",
                "due_date": (timezone.localdate() + timedelta(days=6)).isoformat(),
                "user": get_user_model()
                .objects.create_user(
                    username="attacker",
                    email="attacker@example.com",
                    password="Strong-password-123!",
                )
                .pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        goal = Goal.objects.get(pk=response.data["id"])
        self.assertEqual(goal.user, user)
        self.assertEqual(goal.title, "Learn Rust and build projects")
        self.assertEqual(goal.description, "")
        self.assertEqual(goal.due_date.isoformat(), response.data["due_date"])

    def test_goal_creation_rejects_due_date_today_or_in_the_past(self):
        user = get_user_model().objects.create_user(
            username="goal-date-user",
            email="goal-date-user@example.com",
            password="Strong-password-123!",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

        for due_date in (
            timezone.localdate(),
            timezone.localdate() - timedelta(days=1),
        ):
            with self.subTest(due_date=due_date):
                response = client.post(
                    reverse("goal-list"),
                    {"title": "Invalid due date", "due_date": due_date.isoformat()},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("due_date", response.data)

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


class GoalStartDateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="sd-owner", email="sd@example.com", password="Strong-password-123!"
        )
        self.other = user_model.objects.create_user(
            username="sd-other", email="sd2@example.com", password="Strong-password-123!"
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}"
        )

    def test_start_date_defaults_to_today(self):
        response = self.client.post(reverse("goal-list"), {"title": "G"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["start_date"], timezone.localdate().isoformat())

    def test_explicit_start_date_is_preserved(self):
        response = self.client.post(
            reverse("goal-list"),
            {"title": "G", "start_date": "2030-01-15"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["start_date"], "2030-01-15")

    def test_invalid_start_date_rejected(self):
        response = self.client.post(
            reverse("goal-list"), {"title": "G", "start_date": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)

    def test_update_start_date(self):
        goal = Goal.objects.create(user=self.user, title="G")
        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]),
            {"start_date": "2031-02-03"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.start_date.isoformat(), "2031-02-03")

    def test_cannot_update_other_users_goal(self):
        goal = Goal.objects.create(user=self.other, title="G")
        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]),
            {"start_date": "2031-02-03"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_requires_authentication(self):
        goal = Goal.objects.create(user=self.user, title="G")
        response = APIClient().get(reverse("goal-detail", args=[goal.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_due_date_validation_unchanged(self):
        response = self.client.post(
            reverse("goal-list"),
            {"title": "G", "due_date": timezone.localdate().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoalTimelineMotivationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="tl-owner", email="tl@example.com", password="Strong-password-123!"
        )
        self.other = user_model.objects.create_user(
            username="tl-other", email="tl2@example.com", password="Strong-password-123!"
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}"
        )

    def test_model_defaults(self):
        goal = Goal.objects.create(user=self.user, title="G")
        self.assertEqual(goal.timeline, Goal.Timeline.SHORT_TERM)
        self.assertEqual(goal.motivation, "")

    def test_valid_timeline_values_pass_model_validation(self):
        for value in ("short_term", "mid_term", "long_term"):
            with self.subTest(value=value):
                Goal(user=self.user, title="G", timeline=value).full_clean()

    def test_invalid_timeline_fails_model_validation(self):
        with self.assertRaises(ValidationError):
            Goal(user=self.user, title="G", timeline="someday").full_clean()

    def test_create_defaults_when_fields_omitted(self):
        response = self.client.post(reverse("goal-list"), {"title": "G"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["timeline"], "short_term")
        self.assertEqual(response.data["motivation"], "")

    def test_create_with_timeline_and_motivation(self):
        for value in ("short_term", "mid_term", "long_term"):
            with self.subTest(value=value):
                response = self.client.post(
                    reverse("goal-list"),
                    {"title": "G", "timeline": value, "motivation": "Because"},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                goal = Goal.objects.get(pk=response.data["id"])
                self.assertEqual(goal.timeline, value)
                self.assertEqual(goal.motivation, "Because")

    def test_invalid_timeline_rejected(self):
        response = self.client.post(
            reverse("goal-list"), {"title": "G", "timeline": "someday"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timeline", response.data)

    def test_update_timeline_and_motivation(self):
        goal = Goal.objects.create(user=self.user, title="G", due_date=None)
        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]),
            {"timeline": "long_term", "motivation": "Why"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.timeline, "long_term")
        self.assertEqual(goal.motivation, "Why")

        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]), {"motivation": ""}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.motivation, "")
        self.assertEqual(goal.timeline, "long_term")

    def test_timeline_is_not_derived_from_dates(self):
        response = self.client.post(
            reverse("goal-list"),
            {
                "title": "G",
                "timeline": "long_term",
                "start_date": "2030-01-01",
                "due_date": "2030-01-08",
            },
            format="json",
        )
        self.assertEqual(response.data["timeline"], "long_term")

    def test_serialization_in_list_and_detail(self):
        goal = Goal.objects.create(
            user=self.user, title="G", timeline="mid_term", motivation="M"
        )
        listed = self.client.get(reverse("goal-list")).data[0]
        detail = self.client.get(reverse("goal-detail", args=[goal.pk])).data
        for data in (listed, detail):
            self.assertEqual(data["timeline"], "mid_term")
            self.assertEqual(data["motivation"], "M")
            self.assertIn("start_date", data)
            self.assertIn("due_date", data)

    def test_existing_goal_without_new_values_is_compatible(self):
        goal = Goal.objects.create(
            user=self.user, title="Legacy", description="d", start_date="2026-01-01"
        )
        Goal.objects.filter(pk=goal.pk).update(timeline="short_term", motivation="")
        data = self.client.get(reverse("goal-detail", args=[goal.pk])).data
        self.assertEqual(data["title"], "Legacy")
        self.assertEqual(data["description"], "d")
        self.assertEqual(data["timeline"], "short_term")
        self.assertEqual(data["motivation"], "")

    def test_cannot_update_other_users_timeline(self):
        goal = Goal.objects.create(user=self.other, title="G")
        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]),
            {"timeline": "long_term"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GoalCategoryTests(TestCase):
    expected = {
        "health_wellness": "Health & Wellness",
        "career_learning": "Career & Learning",
        "family_relationships": "Family & Relationships",
        "financial_life": "Financial Life",
        "travel_experiences": "Travel & Experiences",
        "personal_life": "Personal Life",
    }

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="cat-owner",
            email="cat@example.com",
            password="Strong-password-123!",
        )
        self.other = user_model.objects.create_user(
            username="cat-other",
            email="cat2@example.com",
            password="Strong-password-123!",
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}"
        )

    def test_seeded_categories_are_listed_in_order(self):
        response = self.client.get(reverse("goal-category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([c["key"] for c in response.data], list(self.expected))
        self.assertEqual(
            {c["key"]: c["name"] for c in response.data}, self.expected
        )
        self.assertTrue(all(c["description"] for c in response.data))
        self.assertEqual(set(response.data[0]), {"key", "name", "description"})

    def test_inactive_categories_are_hidden_from_listing(self):
        GoalCategory.objects.filter(key="personal_life").update(is_active=False)
        response = self.client.get(reverse("goal-category-list"))
        self.assertNotIn("personal_life", [c["key"] for c in response.data])
        self.assertEqual(len(response.data), 5)

    def test_category_endpoint_requires_authentication_and_is_read_only(self):
        url = reverse("goal-category-list")
        self.assertEqual(
            APIClient().get(url).status_code, status.HTTP_401_UNAUTHORIZED
        )
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(
                    response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
                )
        self.assertEqual(GoalCategory.objects.count(), 6)

    def test_seed_is_idempotent_and_preserves_existing_rows(self):
        seed_module = import_module("goals.migrations.0008_seed_goal_categories")
        category = GoalCategory.objects.get(key="health_wellness")
        GoalCategory.objects.filter(pk=category.pk).update(name="Edited")
        goal = Goal.objects.create(user=self.user, title="G", category=category)

        seed_module.seed_categories(apps, connection.schema_editor())

        self.assertEqual(GoalCategory.objects.count(), 6)
        category.refresh_from_db()
        self.assertEqual(category.name, "Edited")
        goal.refresh_from_db()
        self.assertEqual(goal.category_id, category.pk)

    def test_create_goal_with_category(self):
        response = self.client.post(
            reverse("goal-list"),
            {"title": "Run 5k", "category": "health_wellness"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], "health_wellness")
        self.assertEqual(response.data["category_detail"]["name"], "Health & Wellness")
        goal = Goal.objects.get(pk=response.data["id"])
        self.assertEqual(goal.category.key, "health_wellness")
        self.assertEqual(goal.user, self.user)

    def test_category_is_optional_and_existing_goals_stay_compatible(self):
        legacy = Goal.objects.create(user=self.user, title="Legacy")
        self.assertIsNone(legacy.category)
        response = self.client.get(reverse("goal-detail", args=[legacy.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["category"])
        self.assertIsNone(response.data["category_detail"])

        created = self.client.post(reverse("goal-list"), {"title": "G"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(created.data["category"])

        explicit_null = self.client.post(
            reverse("goal-list"), {"title": "G2", "category": None}, format="json"
        )
        self.assertEqual(explicit_null.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(explicit_null.data["category"])

        # DRF treats an empty string on a nullable relation as "no category".
        empty = self.client.post(
            reverse("goal-list"), {"title": "G3", "category": ""}, format="json"
        )
        self.assertEqual(empty.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(empty.data["category"])

    def test_update_changes_and_clears_category_without_touching_other_fields(self):
        goal = Goal.objects.create(
            user=self.user,
            title="G",
            category=GoalCategory.objects.get(key="health_wellness"),
        )
        url = reverse("goal-detail", args=[goal.pk])

        response = self.client.patch(url, {"category": "financial_life"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"], "financial_life")

        response = self.client.patch(url, {"title": "Renamed"}, format="json")
        self.assertEqual(response.data["category"], "financial_life")

        response = self.client.patch(url, {"category": None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertIsNone(goal.category)
        self.assertEqual(goal.title, "Renamed")

    def test_invalid_unknown_and_inactive_categories_are_rejected(self):
        GoalCategory.objects.filter(key="travel_experiences").update(is_active=False)
        for value in ("nope", "travel_experiences", 1, "Has Space"):
            with self.subTest(value=value):
                response = self.client.post(
                    reverse("goal-list"),
                    {"title": "G", "category": value},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("category", response.data)
        self.assertFalse(Goal.objects.filter(title="G").exists())

    def test_category_updates_are_scoped_to_the_owner(self):
        goal = Goal.objects.create(user=self.other, title="Theirs")
        response = self.client.patch(
            reverse("goal-detail", args=[goal.pk]),
            {"category": "personal_life"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        goal.refresh_from_db()
        self.assertIsNone(goal.category)

    def test_goal_list_category_filter(self):
        health = GoalCategory.objects.get(key="health_wellness")
        mine = Goal.objects.create(user=self.user, title="Mine", category=health)
        Goal.objects.create(user=self.user, title="Uncategorised")
        Goal.objects.create(user=self.other, title="Theirs", category=health)

        response = self.client.get(reverse("goal-list") + "?category=health_wellness")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([g["id"] for g in response.data], [mine.pk])

        response = self.client.get(reverse("goal-list") + "?category=financial_life")
        self.assertEqual(response.data, [])

        response = self.client.get(reverse("goal-list") + "?category=bogus")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(len(self.client.get(reverse("goal-list")).data), 2)

    def test_category_with_goals_cannot_be_deleted(self):
        category = GoalCategory.objects.get(key="personal_life")
        Goal.objects.create(user=self.user, title="G", category=category)
        with self.assertRaises(ProtectedError):
            category.delete()


class GoalDeleteTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="del-owner", email="del@example.com", password="Strong-password-123!"
        )
        self.other = user_model.objects.create_user(
            username="del-other", email="del2@example.com", password="Strong-password-123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.goal = Goal.objects.create(user=self.user, title="Mine")

    def url(self, goal):
        return reverse("goal-detail", args=[goal.pk])

    def test_owner_can_delete_goal(self):
        response = self.client.delete(self.url(self.goal))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Goal.objects.filter(pk=self.goal.pk).exists())

    def test_delete_requires_authentication(self):
        response = APIClient().delete(self.url(self.goal))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Goal.objects.filter(pk=self.goal.pk).exists())

    def test_cannot_delete_other_users_goal(self):
        theirs = Goal.objects.create(user=self.other, title="Theirs")
        response = self.client.delete(self.url(theirs))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Goal.objects.filter(pk=theirs.pk).exists())

    def test_delete_missing_goal_returns_404(self):
        response = self.client.delete(reverse("goal-detail", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_linked_tasks_are_kept_and_become_independent(self):
        from datetime import timedelta

        from django.utils import timezone

        from tasks.models import Task

        start = timezone.now()
        task = Task.objects.create(
            user=self.user,
            title="T",
            goal=self.goal,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
        )
        self.client.delete(self.url(self.goal))
        task.refresh_from_db()
        self.assertIsNone(task.goal_id)
