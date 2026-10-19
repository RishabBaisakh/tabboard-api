from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from onboarding.models import OnboardingOption, OnboardingQuestion, OnboardingResponse
from users.models import Interest, PersonalityTag, UserProfile


class OnboardingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="onboarding-user",
            email="onboarding-user@example.com",
            password="Strong-password-123!",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-onboarding-user",
            email="other-onboarding-user@example.com",
            password="Strong-password-123!",
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}"
        )

        self.questions = []
        self.options = {}
        for index, (key, selection, limit) in enumerate(
            (("required_one", "single", 1), ("required_many", "multiple", 3)),
            start=1,
        ):
            question = OnboardingQuestion.objects.create(
                key=key,
                text=f"Question {index}",
                selection_type=selection,
                max_selections=limit,
                is_required=True,
                is_active=True,
            )
            self.questions.append(question)
            self.options[key] = [
                OnboardingOption.objects.create(
                    question=question,
                    key=f"{key}_option_{option_index}",
                    label=f"{key} option {option_index}",
                )
                for option_index in range(1, 5)
            ]

        self.interests = [
            Interest.objects.create(key="reading", name="Reading"),
            Interest.objects.create(key="fitness", name="Fitness"),
        ]
        self.tags = [
            PersonalityTag.objects.create(key="curious", name="Curious"),
            PersonalityTag.objects.create(key="creative", name="Creative"),
        ]

    def _submit_all_required_answers(self):
        return self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": question.key,
                        "selected_option_ids": [self.options[question.key][0].pk],
                    }
                    for question in self.questions
                ],
            },
            format="json",
        )

    def test_get_returns_all_pages_in_one_response_and_user_selections(self):
        self.user.profile.interests.add(self.interests[0])
        self.user.profile.personality_tags.add(self.tags[0])
        response = OnboardingResponse.objects.create(
            user=self.user,
            question=self.questions[0],
        )
        response.selected_options.add(self.options[self.questions[0].key][1])

        result = self.client.get(reverse("onboarding"))

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(len(result.data["basic_info"]["questions"]), 2)
        self.assertEqual(
            result.data["basic_info"]["questions"][0]["selected_option_ids"],
            [self.options[self.questions[0].key][1].pk],
        )
        self.assertEqual(
            result.data["interests"]["selected_ids"], [self.interests[0].pk]
        )
        self.assertEqual(
            result.data["personality_tags"]["selected_ids"], [self.tags[0].pk]
        )
        self.assertIn("profile", result.data)
        self.assertEqual(result.data["is_complete"], False)

    def test_get_does_not_create_missing_profile(self):
        profile_id = self.user.profile.pk
        self.user.profile.delete()

        response = self.client.get(reverse("onboarding"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(UserProfile.objects.filter(pk=profile_id).exists())

    def test_unauthenticated_requests_are_rejected(self):
        client = APIClient()
        self.assertEqual(
            client.get(reverse("onboarding")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            client.get(reverse("onboarding-status")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_steps_save_and_resume_without_early_completion(self):
        basic = self._submit_all_required_answers()
        self.assertEqual(basic.status_code, status.HTTP_200_OK)
        self.assertFalse(basic.data["is_complete"])
        self.assertEqual(OnboardingResponse.objects.filter(user=self.user).count(), 2)

        resumed = self.client.get(reverse("onboarding"))
        self.assertEqual(
            resumed.data["basic_info"]["questions"][0]["selected_option_ids"],
            [self.options[self.questions[0].key][0].pk],
        )

        interest_response = self.client.patch(
            reverse("onboarding"),
            {"step": "interests", "selected_ids": [self.interests[0].pk]},
            format="json",
        )
        self.assertEqual(interest_response.status_code, status.HTTP_200_OK)
        self.assertFalse(interest_response.data["is_complete"])

        tags_response = self.client.patch(
            reverse("onboarding"),
            {"step": "personality_tags", "selected_ids": [self.tags[0].pk]},
            format="json",
        )
        self.assertEqual(tags_response.status_code, status.HTTP_200_OK)
        self.assertTrue(tags_response.data["is_complete"])
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.onboarding_completed_at)

        status_response = self.client.get(reverse("onboarding-status"))
        self.assertEqual(status_response.data, {"is_complete": True})

    def test_answers_replace_previous_options_without_duplicate_response(self):
        question = self.questions[0]
        url = reverse("onboarding")
        for option in self.options[question.key][:2]:
            response = self.client.patch(
                url,
                {
                    "step": "questions",
                    "answers": [
                        {
                            "question_key": question.key,
                            "selected_option_ids": [option.pk],
                        }
                    ],
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        saved = OnboardingResponse.objects.get(user=self.user, question=question)
        self.assertEqual(saved.selected_options.count(), 1)
        self.assertEqual(
            saved.selected_options.get().pk, self.options[question.key][1].pk
        )

    def test_single_and_multiple_selection_limits_are_enforced(self):
        single_question, multiple_question = self.questions
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": single_question.key,
                        "selected_option_ids": [
                            self.options[single_question.key][0].pk,
                            self.options[single_question.key][1].pk,
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": multiple_question.key,
                        "selected_option_ids": [
                            item.pk for item in self.options[multiple_question.key]
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_option_from_another_question_is_rejected(self):
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": self.questions[0].key,
                        "selected_option_ids": [
                            self.options[self.questions[1].key][0].pk
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_questionnaire_and_profile_options_are_rejected(self):
        question = self.questions[0]
        question.is_active = False
        question.save(update_fields=["is_active"])
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": question.key,
                        "selected_option_ids": [self.options[question.key][0].pk],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        question.is_active = True
        question.save(update_fields=["is_active"])
        option = self.options[self.questions[0].key][0]
        option.is_active = False
        option.save(update_fields=["is_active"])
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": self.questions[0].key,
                        "selected_option_ids": [option.pk],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        inactive_interest = self.interests[0]
        inactive_interest.is_active = False
        inactive_interest.save(update_fields=["is_active"])
        response = self.client.patch(
            reverse("onboarding"),
            {"step": "interests", "selected_ids": [inactive_interest.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        inactive_tag = self.tags[0]
        inactive_tag.is_active = False
        inactive_tag.save(update_fields=["is_active"])
        response = self.client.patch(
            reverse("onboarding"),
            {"step": "personality_tags", "selected_ids": [inactive_tag.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_data_is_isolated(self):
        self.user.profile.interests.add(self.interests[0])
        self.user.profile.personality_tags.add(self.tags[0])
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "questions",
                "answers": [
                    {
                        "question_key": self.questions[0].key,
                        "selected_option_ids": [
                            self.options[self.questions[0].key][0].pk
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        other_client = APIClient()
        other_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.other_user)}"
        )
        other_result = other_client.get(reverse("onboarding"))
        self.assertEqual(
            other_result.data["basic_info"]["questions"][0]["selected_option_ids"],
            [],
        )
        self.assertEqual(other_result.data["interests"]["selected_ids"], [])
        self.assertEqual(other_result.data["personality_tags"]["selected_ids"], [])
        self.assertEqual(
            OnboardingResponse.objects.filter(user=self.other_user).count(),
            0,
        )

    def test_invalid_step_and_unexpected_fields_are_rejected(self):
        response = self.client.patch(
            reverse("onboarding"),
            {"step": "unknown", "selected_ids": [self.interests[0].pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_basic_info_does_not_accept_question_answers(self):
        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "basic_info",
                "bio": "Profile details",
                "answers": [
                    {
                        "question_key": self.questions[0].key,
                        "selected_option_ids": [
                            self.options[self.questions[0].key][0].pk
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("answers", response.data["non_field_errors"][0])

        response = self.client.patch(
            reverse("onboarding"),
            {"step": "basic_info", "display_name": "Rishab"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            reverse("onboarding"),
            {
                "step": "interests",
                "selected_ids": [self.interests[0].pk],
                "user_id": self.other_user.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_interest_and_tag_steps_are_rejected(self):
        for step in ("interests", "personality_tags"):
            with self.subTest(step=step):
                response = self.client.patch(
                    reverse("onboarding"),
                    {"step": step, "selected_ids": []},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_timezone_and_unknown_basic_info_fields_are_rejected(self):
        invalid_timezone = self.client.patch(
            reverse("onboarding"),
            {"step": "basic_info", "time_zone": "Invalid/Zone"},
            format="json",
        )
        self.assertEqual(invalid_timezone.status_code, status.HTTP_400_BAD_REQUEST)

        unknown_field = self.client.patch(
            reverse("onboarding"),
            {"step": "basic_info", "user_id": self.other_user.pk},
            format="json",
        )
        self.assertEqual(unknown_field.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completed_onboarding_stays_complete_after_later_changes(self):
        self._submit_all_required_answers()
        self.client.patch(
            reverse("onboarding"),
            {"step": "interests", "selected_ids": [self.interests[0].pk]},
            format="json",
        )
        self.client.patch(
            reverse("onboarding"),
            {"step": "personality_tags", "selected_ids": [self.tags[0].pk]},
            format="json",
        )

        response = self.client.patch(
            reverse("onboarding"),
            {"step": "basic_info", "bio": "Updated after onboarding"},
            format="json",
        )

        self.assertTrue(response.data["is_complete"])
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.onboarding_completed_at)


class OnboardingFixtureApiTests(TestCase):
    fixtures = ("onboarding.json",)

    def test_one_get_contains_all_three_onboarding_pages(self):
        user = get_user_model().objects.create_user(
            username="fixture-user",
            email="fixture-user@example.com",
            password="Strong-password-123!",
        )
        Interest.objects.create(key="test-interest", name="Test interest")
        PersonalityTag.objects.create(key="test-tag", name="Test tag")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

        response = client.get(reverse("onboarding"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["basic_info"]["questions"]), 7)
        self.assertEqual(
            sum(
                len(question["options"])
                for question in response.data["basic_info"]["questions"]
            ),
            41,
        )
        self.assertEqual(len(response.data["interests"]["options"]), 1)
        self.assertEqual(len(response.data["personality_tags"]["options"]), 1)
