from django.db import models
from meetings.models import Meeting
from django.contrib.auth import get_user_model
User = get_user_model()

class Alert(models.Model):
    ALERT_TYPES = [
        ('inactivity', 'Inactivity'),
        ('recording_failed', 'Recording Failed'),
        ('meeting_start', 'Meeting Start Reminder'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=50, choices=ALERT_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)