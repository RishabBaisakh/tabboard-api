from datetime import date, datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from tasks.models import Task
from tasks.serializers import TaskSerializer


def _parse_date_param(query_params, name):
    values = query_params.getlist(name)
    if len(values) > 1:
        raise ValidationError({name: "Provide this parameter only once."})
    if not values:
        return None

    try:
        parsed = date.fromisoformat(values[0])
    except ValueError as error:
        raise ValidationError({name: "Use the YYYY-MM-DD date format."}) from error
    if parsed.isoformat() != values[0]:
        raise ValidationError({name: "Use the YYYY-MM-DD date format."})
    return parsed


class UserTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "put", "patch", "delete", "head", "options")

    def get_queryset(self):
        queryset = Task.objects.filter(user=self.request.user).select_related("goal")

        if self.action == "list":
            start_date = _parse_date_param(self.request.query_params, "start_date")
            end_date = _parse_date_param(self.request.query_params, "end_date")
            if end_date is not None and start_date is None:
                raise ValidationError(
                    {"start_date": "Required when end_date is provided."}
                )
            if start_date is None:
                start_date = timezone.localdate()
            if end_date is None:
                end_date = start_date
            if end_date < start_date:
                raise ValidationError({"end_date": "Must be on or after start_date."})
            if end_date == date.max:
                raise ValidationError({"end_date": "Date is out of range."})

            current_timezone = timezone.get_current_timezone()
            range_start = timezone.make_aware(
                datetime.combine(start_date, time.min), current_timezone
            )
            range_end = timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), time.min),
                current_timezone,
            )
            queryset = queryset.filter(
                scheduled_start__lt=range_end,
                scheduled_end__gt=range_start,
            )

        status_value = self.request.query_params.get("status")
        if status_value:
            if status_value not in Task.Status.values:
                raise ValidationError({"status": "Invalid task status."})
            queryset = queryset.filter(status=status_value)

        priority = self.request.query_params.get("priority")
        if priority:
            if priority not in Task.Priority.values:
                raise ValidationError({"priority": "Invalid task priority."})
            queryset = queryset.filter(priority=priority)

        goal_id = self.request.query_params.get("goal")
        if goal_id:
            if not goal_id.isdecimal() or int(goal_id) < 1:
                raise ValidationError({"goal": "Goal must be a positive integer ID."})
            queryset = queryset.filter(goal_id=int(goal_id))

        date_after = self.request.query_params.get("scheduled_start_after")
        if date_after:
            parsed = parse_datetime(date_after)
            if parsed is None or timezone.is_naive(parsed):
                raise ValidationError(
                    {"scheduled_start_after": "Use a timezone-aware ISO-8601 datetime."}
                )
            queryset = queryset.filter(scheduled_start__gte=parsed)

        date_before = self.request.query_params.get("scheduled_start_before")
        if date_before:
            parsed = parse_datetime(date_before)
            if parsed is None or timezone.is_naive(parsed):
                raise ValidationError(
                    {
                        "scheduled_start_before": "Use a timezone-aware ISO-8601 datetime."
                    }
                )
            queryset = queryset.filter(scheduled_start__lte=parsed)

        return queryset.order_by("-created_at", "-id")
