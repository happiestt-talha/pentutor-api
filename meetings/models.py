# meeting/models.py

from django.db import models
from authentication.models import User
from courses.models import Course,Enrollment,Video,Progress
from payments.models import Payment

from django.utils import timezone
import uuid
import random
import string


class Meeting(models.Model):
    MEETING_STATUS = [
        ('waiting', 'Waiting Room'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    MEETING_TYPES = [
        ('instant', 'Instant Meeting'),
        ('scheduled', 'Scheduled Meeting'),
        ('lecture', 'Course Lecture'),
    ]
    
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_meetings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='meetings', null=True, blank=True)
    title = models.CharField(max_length=255)
    password = models.CharField(max_length=20, blank=True)
    meeting_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPES, default='instant')
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=MEETING_STATUS, default='waiting')
    access_type = models.CharField(max_length=20, choices=[
    ('public', 'Public'),
    ('private', 'Private'),
    ('approval_required', 'Approval Required'),
], default='public')
    is_password_required = models.BooleanField(default=False)
    # Recording for course lectures
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True, null=True)
    recording_duration = models.CharField(max_length=10, blank=True)  # Format: "10:30"

    # Admin control
    allow_student_recording_access = models.BooleanField(default=False)
    
    # Meeting Settings
    max_participants = models.IntegerField(default=100)
    is_waiting_room_enabled = models.BooleanField(default=False)
    allow_participant_share_screen = models.BooleanField(default=True)
    allow_participant_unmute = models.BooleanField(default=True)
    enable_chat = models.BooleanField(default=True)
    enable_reactions = models.BooleanField(default=True)
    
    # Timestamps
    scheduled_time = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # def save(self, *args, **kwargs):
        # if not self.meeting_id:
        #     self.meeting_id = str(uuid.uuid4())  # Use UUID instead of formatted string
        # if not self.password and self.is_password_required:
        #     print("Password created")
        #     self.password = self.generate_password()
        # super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.meeting_id:
            self.meeting_id = self.generate_meeting_id()
        if not self.password and self.is_password_required:
            print("save passwrod")
            self.password = self.generate_password()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_meeting_id():
        while True:
            meeting_id = ''.join(random.choices(string.digits, k=10))
            formatted_id = f"{meeting_id[:3]}-{meeting_id[3:6]}-{meeting_id[6:]}"
            if not Meeting.objects.filter(meeting_id=formatted_id).exists():
                return formatted_id
    
    @staticmethod
    def generate_password():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    

    def get_enrolled_students(self):
        """Get students enrolled in course for lecture meetings"""
        if self.meeting_type == 'lecture' and self.course:
            return self.course.enrollments.filter(studentt__student_profile__isnull=False
        ).select_related('student__student_profile')
        return []

    def start_meeting(self):
        self.status = 'active'
        self.started_at = timezone.now()
        self.save()
    
    def end_meeting(self):
        self.status = 'ended'
        self.ended_at = timezone.now()
        self.save()
        # Leave all participants
        self.participants.filter(left_at__isnull=True).update(left_at=timezone.now())
        
        # Create recorded video for course lectures
        if self.meeting_type == 'lecture' and self.course and self.is_recorded:
            self.create_recorded_video()
    
    def create_recorded_video(self):
        """Create a video record from meeting recording"""
        if self.recording_url and self.course:
            video = Video.objects.create(
                course=self.course,
                title=f"Recorded Lecture: {self.title}",
                description=f"Live lecture recorded on {self.started_at.strftime('%Y-%m-%d %H:%M')}",
                video_file=self.recording_url,  # This would need to be handled properly
                duration=self.recording_duration or "0:00",
                order=self.course.videos.count() + 1
            )
            return video
        return None
    
    def can_user_join(self, user):
        """Check if user can join the meeting"""
        # Host can always join
        if self.host == user:
            return True, "Host can join"
        
        # For course lectures, check enrollment and payment
        if self.meeting_type == 'lecture' and self.course:
            # Check if user is enrolled in the course
          
            try:
                enrollment = Enrollment.objects.get(student=user, course=self.course,student__student_profile__isnull=False)
            except Enrollment.DoesNotExist:
                return False, "You are not enrolled in this course"
            
            # Check payment for paid courses
            if self.course.course_type == 'paid':
              
                payment_exists = Payment.objects.filter(
                    user=user,
                    is_successful=True,
                    # You might want to link payment to course instead of meeting
                ).exists()
                
                if not payment_exists:
                    return False, "Please complete payment first to attend this lecture"
        
        return True, "Can join"
    
    def __str__(self):
        return f"{self.title} - {self.host.email}"
    
    class Meta:
        ordering = ['-scheduled_time']


class Participant(models.Model):
    ROLES = [
        ('host', 'Host'),
        ('co_host', 'Co-Host'),
        ('participant', 'Participant'),
    ]
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLES, default='participant')
    
    # Status Controls
    is_muted = models.BooleanField(default=False)
    is_video_on = models.BooleanField(default=True)
    is_hand_raised = models.BooleanField(default=False)
    is_sharing_screen = models.BooleanField(default=False)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['meeting', 'user']
    
    def leave_meeting(self):
        self.left_at = timezone.now()
        self.is_sharing_screen = False
        self.save()
        
        # Update progress for course lectures
        if self.meeting.meeting_type == 'lecture' and self.meeting.course:
            self.update_course_progress()
    
    def update_course_progress(self):
        """Update student progress when leaving a lecture"""
        if self.role == 'participant':  # Only for students
            Progress.objects.get_or_create(
                student=self.user,
                course=self.meeting.course,
                defaults={'completed_at': timezone.now()}
            )
    
    @property
    def is_active(self):
        return self.left_at is None
    
    def __str__(self):
        return f"{self.user.username} in {self.meeting.title}"


class MeetingRecording(models.Model):
    """Model to store meeting recording details"""
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='recording')
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    duration = models.CharField(max_length=10, blank=True)  # Format: "10:30"
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recording for {self.meeting.title}"


class MeetingChat(models.Model):
    """Model to store chat messages during meetings"""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}..."
    
# Add after MeetingChat model
class MeetingInvite(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='invites')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['meeting', 'email']
    
    def __str__(self):
        return f"Invite to {self.email} for {self.meeting.title}"


class JoinRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True)
    guest_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_requests')
    handled_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.guest_name or self.guest_email
    
    def approve(self, handler):
        self.status = 'approved'
        self.handled_by = handler
        self.handled_at = timezone.now()
        self.save()
    
    def deny(self, handler):
        self.status = 'denied'
        self.handled_by = handler
        self.handled_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Join request from {self.display_name} for {self.meeting.title}"