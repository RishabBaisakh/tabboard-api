from django.contrib import admin

from goals.models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "due_date", "created_at")
    search_fields = ("title", "user__email", "user__username")
