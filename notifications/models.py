# notifications/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Course, Video, Quiz
from meetings.models import Meeting

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    """
    Model to store notifications for users in the LMS system
    """
    NOTIFICATION_TYPES = [
        ('video_upload', 'New Video Uploaded'),
        ('quiz_created', 'New Quiz Created'),
        ('student_enrolled', 'Student Enrolled'),
        ('live_class_scheduled', 'Live Class Scheduled'),
        ('payment_completed', 'Payment Completed'),
         ('meeting_start', 'Meeting Start'),
        ('general', 'General Notification'),
    ]
    
    # Who receives the notification
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    # Who triggered the notification (optional)
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_notifications',
        null=True, 
        blank=True
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=30, 
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related objects (optional foreign keys)
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    video = models.ForeignKey(
        Video, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    quiz = models.ForeignKey(
        Quiz, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    meeting = models.ForeignKey(
        Meeting, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Status and timestamps
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    @property
    def time_since_created(self):
        """Get human readable time since notification was created"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"