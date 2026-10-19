from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_future_due_date(value):
    if value <= timezone.localdate():
        raise ValidationError("Due date must be after today.")


class Goal(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
    )
    title = models.CharField(max_length=200)
    due_date = models.DateField(
        null=True,
        blank=True,
        validators=[validate_future_due_date],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title
