from django.db import models
from django.conf import settings


# Create your models here.

class GoogleCredentials(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()
    expiry = models.DateTimeField(null=True, blank=True)
    channel_id = models.CharField(max_length=255, null=True, blank=True)
    resource_id = models.CharField(max_length=255, null=True, blank=True)



class CalendarEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_id = models.CharField(max_length=255, unique=True)  # Google's event ID
    summary = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    updated = models.DateTimeField()  # Google's updated timestamp


#  This model stores the failed jobs
class FailedSync(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_id = models.CharField(max_length=255, null=True, blank=True)
    reason = models.TextField()
    retry_count = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='pending')  # pending, success, failed
