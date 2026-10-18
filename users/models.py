from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80, blank=True)
    time_zone = models.CharField(max_length=50, default="UTC")
    bio = models.CharField(max_length=300, blank=True)
    personality_tags = ArrayField(
        models.CharField(max_length=40),
        default=list,
        blank=True,
    )
    current_interests = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()
