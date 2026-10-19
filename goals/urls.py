from django.urls import path

from goals.views import UserGoalListView

urlpatterns = [
    path("", UserGoalListView.as_view(), name="goal-list"),
]
