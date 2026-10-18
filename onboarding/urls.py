from django.urls import path

from onboarding.views import OnboardingStatusView, OnboardingView

urlpatterns = [
    path("", OnboardingView.as_view(), name="onboarding"),
    path("status/", OnboardingStatusView.as_view(), name="onboarding-status"),
]
