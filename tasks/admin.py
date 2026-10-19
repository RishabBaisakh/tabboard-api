from django.contrib import admin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "status",
        "priority",
        "scheduled_start",
        "scheduled_end",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "user__email", "user__username")
