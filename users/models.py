from django.conf import settings
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
    interests = models.ManyToManyField(
        "users.Interest",
        related_name="profiles",
        blank=True,
    )
    personality_tags = models.ManyToManyField(
        "users.PersonalityTag",
        related_name="profiles",
        blank=True,
    )
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()


class Interest(models.Model):
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class PersonalityTag(models.Model):
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
