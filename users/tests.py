from django.test import override_settings
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase


class AuthenticationEndpointTests(APITestCase):
    def test_signup_returns_jwt_and_authenticates_profile_request(self):
        response = self.client.post(
            reverse("rest_register"),
            {
                "username": "new-user",
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
        profile = self.client.get(reverse("rest_user_details"))
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["email"], "new-user@example.com")

    def test_login_accepts_email_and_password(self):
        from django.contrib.auth import get_user_model

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

    def test_social_routes_resolve(self):
        self.assertEqual(resolve(reverse("google-login")).url_name, "google-login")

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_social_login_reports_missing_provider_configuration(self):
        response = self.client.post(
            reverse("google-login"),
            {"access_token": "provider-token"},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_social_login_accepts_database_provider_configuration(self):
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
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
