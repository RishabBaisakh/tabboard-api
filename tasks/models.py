import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from goals.models import Goal


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_start", "id"]
        indexes = [
            models.Index(fields=["user", "status"], name="task_user_status_idx"),
            models.Index(
                fields=["user", "scheduled_start"],
                name="task_user_start_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(scheduled_end__gt=F("scheduled_start")),
                name="task_end_after_start",
            ),
        ]

    def __str__(self):
        return self.title
