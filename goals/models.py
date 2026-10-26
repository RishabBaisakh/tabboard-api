from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_future_due_date(value):
    if value <= timezone.localdate():
        raise ValidationError("Due date must be after today.")


class GoalCategory(models.Model):
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "goal categories"

    def __str__(self):
        return self.name


class Goal(models.Model):
    class Timeline(models.TextChoices):
        SHORT_TERM = "short_term", "Short-term"
        MID_TERM = "mid_term", "Mid-term"
        LONG_TERM = "long_term", "Long-term"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    start_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(
        null=True,
        blank=True,
        validators=[validate_future_due_date],
    )
    timeline = models.CharField(
        max_length=20,
        choices=Timeline.choices,
        default=Timeline.SHORT_TERM,
    )
    motivation = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        GoalCategory,
        on_delete=models.PROTECT,
        related_name="goals",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title
