from django.conf import settings
from django.db import models


class OnboardingQuestion(models.Model):
    class SelectionType(models.TextChoices):
        SINGLE = "single", "Single selection"
        MULTIPLE = "multiple", "Multiple selections"

    key = models.SlugField(max_length=80, unique=True)
    text = models.CharField(max_length=300)
    selection_type = models.CharField(max_length=10, choices=SelectionType.choices)
    max_selections = models.PositiveSmallIntegerField()
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(selection_type="single", max_selections=1)
                    | models.Q(
                        selection_type="multiple",
                        max_selections__gte=1,
                        max_selections__lte=3,
                    )
                ),
                name="onboarding_question_selection_limit_valid",
            ),
        ]

    def __str__(self):
        return self.text


class OnboardingOption(models.Model):
    question = models.ForeignKey(
        OnboardingQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "key"],
                name="onboarding_option_question_key_unique",
            ),
        ]

    def __str__(self):
        return self.label


class OnboardingResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_responses",
    )
    question = models.ForeignKey(
        OnboardingQuestion,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    selected_options = models.ManyToManyField(
        OnboardingOption,
        related_name="responses",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="onboarding_response_user_question_unique",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.question.key}"
