# emial_automation/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from courses.models import Course, Enrollment
from payments.models import Payment

User = get_user_model()

class EmailTemplate(models.Model):
    """Email templates for different scenarios"""
    EMAIL_TYPES = [
        ('enrollment', 'Course Enrollment'),
        ('demo_completed', 'Post-Demo Class'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('weekly_progress', 'Weekly Progress'),
        ('new_content', 'New Content Notification'),
    ]
    
    name = models.CharField(max_length=100)
    email_type = models.CharField(max_length=20, choices=EMAIL_TYPES, unique=True)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_email_type_display()})"
    
    class Meta:
        db_table = 'email_templates'


class EmailLog(models.Model):
    """Log all sent emails for tracking and debugging"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    email_type = models.CharField(max_length=20, choices=EmailTemplate.EMAIL_TYPES)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Related objects for context
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient.email} - {self.status}"
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']


class EmailPreference(models.Model):
    """User email preferences and unsubscribe management"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Email type preferences
    enrollment_emails = models.BooleanField(default=True)
    demo_emails = models.BooleanField(default=True)
    payment_emails = models.BooleanField(default=True)
    progress_emails = models.BooleanField(default=True)
    content_emails = models.BooleanField(default=True)
    
    # General preferences
    is_subscribed = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Email preferences for {self.user.email}"
    
    def unsubscribe(self):
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save()
    
    def can_receive_email(self, email_type):
        if not self.is_subscribed:
            return False
        
        type_mapping = {
            'enrollment': self.enrollment_emails,
            'demo_completed': self.demo_emails,
            'payment_confirmation': self.payment_emails,
            'weekly_progress': self.progress_emails,
            'new_content': self.content_emails,
        }
        
        return type_mapping.get(email_type, True)
    
    class Meta:
        db_table = 'email_preferences'


class WeeklyProgressReport(models.Model):
    """Track weekly progress for students"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    week_start = models.DateField()
    week_end = models.DateField()
    
    # Progress metrics
    videos_completed = models.IntegerField(default=0)
    total_videos = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    total_quizzes = models.IntegerField(default=0)
    assignments_completed = models.IntegerField(default=0)
    total_assignments = models.IntegerField(default=0)
    
    # Time spent (in minutes)
    time_spent = models.IntegerField(default=0)
    
    # Report status
    report_generated = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Weekly progress for {self.user.email} - {self.course.title} ({self.week_start})"
    
    @property
    def completion_percentage(self):
        total_items = self.total_videos + self.total_quizzes + self.total_assignments
        completed_items = self.videos_completed + self.quizzes_completed + self.assignments_completed
        if total_items == 0:
            return 0
        return round((completed_items / total_items) * 100, 2)
    
    class Meta:
        db_table = 'weekly_progress_reports'
        unique_together = ['user', 'course', 'week_start']


class EmailQueue(models.Model):
    """Queue for scheduled emails"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    email_type = models.CharField(max_length=20, choices=EmailTemplate.EMAIL_TYPES)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Scheduling
    scheduled_at = models.DateTimeField()
    max_retries = models.IntegerField(default=3)
    retry_count = models.IntegerField(default=0)
    
    # Context data
    context_data = models.JSONField(default=dict)
    
    # Status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Queued email: {self.email_type} to {self.recipient.email}"
    
    class Meta:
        db_table = 'email_queue'
        ordering = ['priority', 'scheduled_at']
