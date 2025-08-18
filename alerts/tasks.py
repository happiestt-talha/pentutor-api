# alerts/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .redis_client import redis_client
from .models import Alert
from meetings.models import Meeting  
from django.contrib.auth import get_user_model
from .utils import send_live_alert

User = get_user_model()

@shared_task
def check_inactive_students():
    live_meetings = Meeting.objects.filter(is_active=True)

    for meeting in live_meetings:
        participants = meeting.participants.all()  # assuming ManyToManyField
        for user in participants:
            key = f"last_active:{meeting.id}:{user.id}"
            last_seen = redis_client.get(key)

            if not last_seen:
                continue

            try:
                last_seen = timezone.datetime.fromisoformat(last_seen)
            except Exception:
                continue

            if timezone.now() - last_seen > timedelta(minutes=3):
                # ✅ Create alert with real user instance
                Alert.objects.create(
                    user=meeting.host,  # ✅ host is a real user instance
                    type="inactivity",
                    message=f"{user.username} has been inactive for 3+ minutes",
                    meeting=meeting
                )

                # ✅ Send alert to host
                send_live_alert(
                    user_id=meeting.host.id,
                    message=f"{user.username} has been inactive for 3+ minutes",
                    alert_type="inactivity"
                )
