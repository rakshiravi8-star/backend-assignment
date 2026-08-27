import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=50)
    location = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at']
        indexes = [
            models.Index(fields=['starts_at'], name='events_event_starts_idx'),
            models.Index(fields=['location'], name='events_event_location_idx'),
            models.Index(fields=['language'], name='events_event_language_idx'),
            models.Index(fields=['created_by'], name='events_event_created_by_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(starts_at__lt=models.F('ends_at')), name='event_starts_before_ends'),
            models.CheckConstraint(condition=models.Q(capacity__isnull=True) | models.Q(capacity__gt=0), name='event_capacity_positive'),
        ]


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        CANCELED = 'CANCELED', 'Canceled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='enrollments')
    seeker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ENROLLED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'seeker'], name='unique_event_seeker')]
        indexes = [
            models.Index(fields=['event', 'status'], name='events_enroll_event_status_idx'),
            models.Index(fields=['seeker', 'status'], name='events_enroll_seek_status_idx'),
        ]

    def clean(self):
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError('starts_at must be before ends_at.')
        if self.capacity is not None and self.capacity <= 0:
            raise ValidationError('capacity must be positive when provided.')