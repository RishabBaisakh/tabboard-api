from django.contrib import admin

from users.models import Interest, PersonalityTag, UserProfile


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("key", "name")


@admin.register(PersonalityTag)
class PersonalityTagAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("key", "name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "time_zone", "created_at", "updated_at")
    search_fields = ("user__email", "user__username", "display_name")
