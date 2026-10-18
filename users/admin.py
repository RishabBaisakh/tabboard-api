from django.contrib import admin

from users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "time_zone", "created_at", "updated_at")
    search_fields = ("user__email", "user__username", "display_name")
