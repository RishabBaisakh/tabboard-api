from django.contrib import admin

from goals.models import Goal, GoalCategory


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "due_date", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "user__email", "user__username")


@admin.register(GoalCategory)
class GoalCategoryAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active")
    list_filter = ("is_active",)
