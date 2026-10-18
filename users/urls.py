from django.urls import include, path

from users.views import GoogleLogin, UserProfileView

urlpatterns = [
    path("", include("dj_rest_auth.urls")),
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("google/", GoogleLogin.as_view(), name="google-login"),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
]
