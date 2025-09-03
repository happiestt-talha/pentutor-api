# live_classes/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from authentication.models import User, StudentProfile, TeacherProfile
from meetings.models import Meeting
from notifications.models import Notification
import uuid
from datetime import datetime, timedelta


class LiveClassSchedule(models.Model):
    """Individual student's live class schedule created by teacher"""
    
    PAYMENT_FREQUENCY = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    DAYS_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    # Core Information
    schedule_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='live_schedules')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='live_schedules')
    subject = models.CharField(max_length=200)
    
    # Schedule Details
    classes_per_week = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    class_days = models.JSONField(help_text="List of days like ['monday', 'wednesday', 'friday']")
    class_times = models.JSONField(help_text="Dict with day:time mapping like {'monday': '18:00', 'wednesday': '19:00'}")
    class_duration = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    
    # Payment Information
    weekly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    is_active = models.BooleanField(default=True)
    demo_completed = models.BooleanField(default=False)
    demo_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subject} - {self.teacher.full_name} -> {self.student.full_name}"
    
    def get_next_class_date(self):
        """Get the next scheduled class date and time"""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        current_time = datetime.now().time()
        
        # Check if there's a class today that hasn't passed
        today_day = today.strftime('%A').lower()
        if today_day in self.class_days:
            class_time_str = self.class_times.get(today_day)
            if class_time_str:
                class_time = datetime.strptime(class_time_str, '%H:%M').time()
                if current_time < class_time:
                    return datetime.combine(today, class_time)
        
        # Find next class date
        for i in range(1, 8):  # Check next 7 days
            check_date = today + timedelta(days=i)
            check_day = check_date.strftime('%A').lower()
            if check_day in self.class_days:
                class_time_str = self.class_times.get(check_day)
                if class_time_str:
                    class_time = datetime.strptime(class_time_str, '%H:%M').time()
                    return datetime.combine(check_date, class_time)
        
        return None
    
    def create_demo_class(self):
        """Create demo meeting for first class"""
        next_class = self.get_next_class_date()
        if next_class:
            # Convert naive datetime to timezone-aware
            if timezone.is_naive(next_class):
                next_class = timezone.make_aware(next_class)
            meeting = Meeting.objects.create(
                host=self.teacher.user,
                title=f"Demo Class - {self.subject}",
                meeting_type='lecture',
                scheduled_time=next_class,
                is_active=True
            )
            try:

                admin_user = User.objects.filter(role__in ='admin').first()
                if admin_user:
                # Create notification for admin
                    Notification.objects.create(
                        recipient_id=admin_user,  # Assuming admin user ID is 1
                        notification_type='general',
                        title='New Demo Class Scheduled',
                        message=f'Demo class for {self.subject} scheduled between {self.teacher.full_name} and {self.student.full_name} on {next_class.strftime("%Y-%m-%d %H:%M")}'
                    )
                else:
                    print("admin not found")
            except Exception as e:
                print(f"Error creating notification: {e}")
            
            return meeting
        return None
    
    class Meta:
        unique_together = ['teacher', 'student', 'subject']


class LiveClassSubscription(models.Model):
    """Student's subscription for live classes"""
    
    SUBSCRIPTION_TYPE = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    subscription_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    schedule = models.ForeignKey(LiveClassSchedule, on_delete=models.CASCADE, related_name='subscriptions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    
    # Subscription Details
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    classes_included = models.PositiveIntegerField()
    classes_attended = models.PositiveIntegerField(default=0)
    
    # Validity
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Payment Info
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} - {self.schedule.subject} ({self.subscription_type})"
    
    def is_valid(self):
        """Check if subscription is still valid"""
        return self.status == 'active' and self.end_date >= timezone.now().date()
    
    def can_attend_class(self):
        """Check if student can attend more classes"""
        return self.is_valid() and self.classes_attended < self.classes_included
    
    def attend_class(self):
        """Mark a class as attended"""
        if self.can_attend_class():
            self.classes_attended += 1
            if self.classes_attended >= self.classes_included:
                self.status = 'expired'
            self.save()
    
    class Meta:
        ordering = ['-created_at']


class LiveClassSession(models.Model):
    """Individual class session record"""
    
    SESSION_STATUS = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    schedule = models.ForeignKey(LiveClassSchedule, on_delete=models.CASCADE, related_name='sessions')
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, null=True, blank=True)
    subscription = models.ForeignKey(LiveClassSubscription, on_delete=models.CASCADE, null=True, blank=True)
    
    # Session Details
    scheduled_datetime = models.DateTimeField()
    actual_datetime = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(help_text="Actual duration in minutes")
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='scheduled')
    
    # Tracking
    is_demo = models.BooleanField(default=False)
    student_joined = models.BooleanField(default=False)
    teacher_joined = models.BooleanField(default=False)
    join_time_student = models.DateTimeField(null=True, blank=True)
    join_time_teacher = models.DateTimeField(null=True, blank=True)
    
    # Notes and feedback
    teacher_notes = models.TextField(blank=True)
    student_feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session - {self.schedule.subject} on {self.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    def create_meeting(self):
        """Create meeting for this session"""
        if not self.meeting:
            title = f"{'Demo ' if self.is_demo else ''}{self.schedule.subject} Class"
            self.meeting = Meeting.objects.create(
                host=self.schedule.teacher.user,
                title=title,
                meeting_type='lecture',
                scheduled_time=self.scheduled_datetime,
                is_active=True
            )
            self.save()
        return self.meeting
    
    def mark_completed(self):
        """Mark session as completed and update subscription"""
        self.status = 'completed'
        self.save()
        
        if not self.is_demo and self.subscription:
            self.subscription.attend_class()
    
    class Meta:
        ordering = ['scheduled_datetime']


class ClassReschedule(models.Model):
    """Track class reschedule history"""
    
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE, related_name='reschedules')
    original_datetime = models.DateTimeField()
    new_datetime = models.DateTimeField()
    reason = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Teacher or Student
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approved_reschedules', null=True, blank=True)
    
    # Status
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Reschedule: {self.original_datetime} -> {self.new_datetime}"
    
    def approve_reschedule(self, approver):
        """Approve reschedule and update session"""
        self.is_approved = True
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save()
        
        # Update session
        self.session.scheduled_datetime = self.new_datetime
        self.session.status = 'rescheduled'
        self.session.save()
        
        # Notify admin
        Notification.objects.create(
            recipient_id=1,  # Admin
            notification_type='general',
            title='Class Rescheduled',
            message=f'Class rescheduled from {self.original_datetime.strftime("%Y-%m-%d %H:%M")} to {self.new_datetime.strftime("%Y-%m-%d %H:%M")} for {self.session.schedule.subject}'
        )
    
    class Meta:
        ordering = ['-created_at']


class LiveClassPayment(models.Model):
    """Payment records for live classes"""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subscription = models.OneToOneField(LiveClassSubscription, on_delete=models.CASCADE, related_name='payment_record')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    schedule = models.ForeignKey(LiveClassSchedule, on_delete=models.CASCADE)
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Gateway Response
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.amount} - {self.student.full_name} ({self.status})"
    
    def mark_completed(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Notify admin
        Notification.objects.create(
            recipient_id=1,  # Admin
            notification_type='payment_completed',
            title='Live Class Payment Received',
            message=f'Payment of {self.amount} received from {self.student.full_name} for {self.schedule.subject} classes'
        )
    
    class Meta:
        ordering = ['-initiated_at']