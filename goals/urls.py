from django.urls import path

from goals.views import UserGoalDetailView, UserGoalListView

urlpatterns = [
    path("", UserGoalListView.as_view(), name="goal-list"),
    path("<int:pk>/", UserGoalDetailView.as_view(), name="goal-detail"),
]
