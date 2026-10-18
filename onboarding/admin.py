from django.contrib import admin

from onboarding.models import OnboardingOption, OnboardingQuestion, OnboardingResponse


class OnboardingOptionInline(admin.TabularInline):
    model = OnboardingOption
    extra = 0


@admin.register(OnboardingQuestion)
class OnboardingQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "selection_type",
        "max_selections",
        "is_required",
        "is_active",
    )
    list_filter = ("selection_type", "is_required", "is_active")
    search_fields = ("key", "text")
    inlines = (OnboardingOptionInline,)


@admin.register(OnboardingResponse)
class OnboardingResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "updated_at")
    list_filter = ("question",)
    search_fields = ("user__email", "user__username", "question__key")
