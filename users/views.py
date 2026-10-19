from django.conf import settings
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated

from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from users.serializers import UserProfileSerializer
from users.services import get_or_create_user_profile


class SocialProviderNotConfigured(APIException):
    status_code = 503
    default_detail = "Social sign-in is not configured for this provider."
    default_code = "social_provider_not_configured"


class ConfiguredSocialLoginView(SocialLoginView):
    provider = None
    callback_url_setting = None
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        django_request = request._request
        try:
            social_app = get_adapter(django_request).get_app(
                django_request,
                provider=self.provider,
            )
        except SocialApp.DoesNotExist as error:
            raise SocialProviderNotConfigured() from error

        if request.data.get("code"):
            if not social_app.secret:
                raise SocialProviderNotConfigured(
                    "Authorization-code exchange requires a client secret; use a validated provider access token for public clients."
                )
            if not getattr(settings, self.callback_url_setting):
                raise SocialProviderNotConfigured(
                    "Set the provider callback URL before using authorization-code sign-in."
                )
        return super().post(request, *args, **kwargs)


class GoogleLogin(ConfiguredSocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    provider = "google"
    callback_url_setting = "GOOGLE_OAUTH_CALLBACK_URL"

    @property
    def callback_url(self):
        return settings.GOOGLE_OAUTH_CALLBACK_URL


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "put", "patch", "head", "options")

    def get_object(self):
        return get_or_create_user_profile(self.request.user)
