from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from users.serializers import UserProfileSerializer


class AuthenticationEndpointTests(APITestCase):
    def test_signup_without_username_generates_username_and_profile(self):
        response = self.client.post(
            reverse("rest_register"),
            {
                "email": "new-user@example.com",
                "password1": "Strong-password-123!",
                "password2": "Strong-password-123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        user = self.client.get(reverse("rest_user_details"))
        profile = self.client.get(reverse("user-profile"))
        self.assertEqual(user.status_code, status.HTTP_200_OK)
        self.assertTrue(user.data["username"])
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["personality_tags"], [])
        self.assertEqual(profile.data["interests"], [])

    def test_login_accepts_email_and_password(self):
        get_user_model().objects.create_user(
            username="existing-user",
            email="existing-user@example.com",
            password="Strong-password-123!",
        )
        response = self.client.post(
            reverse("rest_login"),
            {
                "email": "existing-user@example.com",
                "password": "Strong-password-123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse("rest_login"),
            {"email": "nobody@example.com", "password": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_social_route_resolves(self):
        self.assertEqual(resolve(reverse("google-login")).url_name, "google-login")

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_social_login_reports_missing_provider_configuration(self):
        response = self.client.post(
            reverse("google-login"),
            {"access_token": "provider-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_social_login_accepts_database_provider_configuration(self):
        from allauth.socialaccount.models import SocialApp
        from unittest.mock import patch

        social_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="test-client",
            secret="test-secret",
        )
        social_app.sites.add(Site.objects.get_current())

        with patch(
            "users.views.SocialLoginView.post",
            return_value=Response({"detail": "delegated"}, status=202),
        ) as social_login:
            response = self.client.post(
                reverse("google-login"),
                {"access_token": "provider-token"},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        social_login.assert_called_once()

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {"APPS": [{"client_id": "extension-client-id"}]}
        }
    )
    def test_google_access_token_flow_accepts_public_client_id(self):
        from unittest.mock import patch

        with patch(
            "users.views.SocialLoginView.post",
            return_value=Response({"detail": "delegated"}, status=202),
        ) as social_login:
            response = self.client.post(
                reverse("google-login"),
                {"access_token": "google-access-token"},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        social_login.assert_called_once()

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {"APPS": [{"client_id": "extension-client-id"}]}
        },
        GOOGLE_OAUTH_CALLBACK_URL="https://extension.chromiumapp.org/",
    )
    def test_public_client_cannot_use_authorization_code_exchange(self):
        response = self.client.post(
            reverse("google-login"),
            {"code": "authorization-code"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {"APPS": [{"client_id": "test-client", "secret": "test-secret"}]}
        },
        GOOGLE_OAUTH_CALLBACK_URL="",
    )
    def test_authorization_code_requires_callback_url(self):
        response = self.client.post(
            reverse("google-login"),
            {"code": "authorization-code"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(CORS_ALLOWED_ORIGINS=["chrome-extension://extension-id"])
    def test_cors_allows_configured_extension_origin(self):
        response = self.client.options(
            reverse("rest_login"),
            HTTP_ORIGIN="chrome-extension://extension-id",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "chrome-extension://extension-id",
        )


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profile-owner",
            email="profile-owner@example.com",
            password="Strong-password-123!",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}"
        )

    def test_user_creation_creates_empty_profile(self):
        profile = self.user.profile
        self.assertEqual(profile.time_zone, "UTC")
        self.assertEqual(profile.personality_tags.count(), 0)
        self.assertEqual(profile.interests.count(), 0)

    def test_unauthenticated_profile_access_is_rejected(self):
        self.client.credentials()
        response = self.client.get(reverse("user-profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_retrieve_and_update_own_profile(self):
        from users.models import Interest, PersonalityTag

        interest = Interest.objects.create(key="productivity", name="Productivity")
        tag = PersonalityTag.objects.create(key="focused", name="Focused")
        url = reverse("user-profile")
        response = self.client.patch(
            url,
            {
                "display_name": "Rishab",
                "time_zone": "America/Toronto",
                "bio": "Building MyTabBoard",
                "personality_tags": [tag.pk],
                "interests": [interest.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user.pk)
        self.assertEqual(response.data["time_zone"], "America/Toronto")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["display_name"], "Rishab")

    def test_profile_owner_cannot_be_changed_by_client(self):
        other_user = get_user_model().objects.create_user(
            username="other-user",
            email="other-user@example.com",
            password="Strong-password-123!",
        )
        response = self.client.patch(
            reverse("user-profile"),
            {"user": other_user.pk, "display_name": "Owner"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.profile.user_id, self.user.pk)
        self.assertNotEqual(self.user.profile.user_id, other_user.pk)

    def test_invalid_time_zone_is_rejected(self):
        response = self.client.patch(
            reverse("user-profile"),
            {"time_zone": "Not/A_Real_Zone"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_zone", response.data)

    def test_profile_interests_have_no_arbitrary_selection_limit(self):
        from users.models import Interest

        interests = [
            Interest.objects.create(key=f"interest-{index}", name=f"Interest {index}")
            for index in range(11)
        ]
        response = self.client.patch(
            reverse("user-profile"),
            {"interests": [interest.pk for interest in interests]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.profile.interests.count(), 11)


class UserProfileSerializerValidationTests(SimpleTestCase):
    def test_valid_iana_time_zone_is_accepted(self):
        serializer = UserProfileSerializer(data={"time_zone": "America/Toronto"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_time_zone_is_rejected(self):
        serializer = UserProfileSerializer(data={"time_zone": "Not/A_Real_Zone"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("time_zone", serializer.errors)
