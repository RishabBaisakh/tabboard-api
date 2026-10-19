from django.urls import include, path
from rest_framework.routers import DefaultRouter

from goals.views import UserGoalListView
from tasks.views import UserTaskViewSet

router = DefaultRouter()
router.register("", UserTaskViewSet, basename="task")

urlpatterns = [
    path("goals/", UserGoalListView.as_view(), name="task-goal-list-compat"),
    path("", include(router.urls)),
]
