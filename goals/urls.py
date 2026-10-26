from django.urls import path

from goals.views import (
    GoalCategoryListView,
    UserGoalDetailView,
    UserGoalListView,
)

urlpatterns = [
    path("", UserGoalListView.as_view(), name="goal-list"),
    path("categories/", GoalCategoryListView.as_view(), name="goal-category-list"),
    path("<int:pk>/", UserGoalDetailView.as_view(), name="goal-detail"),
]
