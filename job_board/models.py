# job_board/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from authentication.models import StudentProfile, TeacherProfile
from courses.models import Course

User = settings.AUTH_USER_MODEL

class JobPost(models.Model):
    TEACHING_MODE_CHOICES = [
        ('remote', 'Remote'),
        ('physical', 'Physical'),
    ]
    
    BUDGET_TYPE_CHOICES = [
        ('per_hour', 'Per Hour'),
        ('per_day', 'Per Day'),
        ('total', 'Total Amount'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE,
        related_name='job_posts'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Subject - can be linked to Course or free text
    course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Select a course if available"
    )
    subject_text = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Or enter subject as text"
    )
    
    # Teaching preferences
    teaching_mode = models.CharField(
        max_length=10, 
        choices=TEACHING_MODE_CHOICES,
        default='remote'
    )
    
    # Budget information
    budget_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    budget_type = models.CharField(
        max_length=10, 
        choices=BUDGET_TYPE_CHOICES,
        default='per_hour'
    )
    
    # Duration
    duration_value = models.PositiveIntegerField(
        help_text="Number of hours/days/sessions"
    )
    duration_unit = models.CharField(
        max_length=20,
        default='hours',
        help_text="e.g., hours, days, sessions"
    )
    
    # Additional information
    additional_notes = models.TextField(blank=True)
    location = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Required for physical teaching mode"
    )
    
    # Status and management
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='open'
    )
    selected_teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_jobs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When do you need this to be completed?"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.student.user.username}"
    
    @property
    def subject_display(self):
        """Return the subject as course name or text"""
        if self.course:
            return self.course.name
        return self.subject_text or "Subject not specified"
    
    @property
    def applications_count(self):
        """Return number of applications for this job"""
        return self.applications.count()
    
    @property
    def is_open(self):
        """Check if job is still accepting applications"""
        return self.status == 'open'


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    # Core relationships
    job_post = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    
    # Application content
    cover_letter = models.TextField(
        help_text="Why are you the right fit for this job?"
    )
    proposed_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank to accept student's budget"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job_post', 'teacher']  # Prevent duplicate applications
        indexes = [
            models.Index(fields=['job_post', 'status']),
            models.Index(fields=['teacher', 'status']),
        ]
    
    def __str__(self):
        return f"{self.teacher.user.username} -> {self.job_post.title}"
    
    @property
    def final_rate(self):
        """Return the proposed rate or job's budget"""
        if self.proposed_rate:
            return self.proposed_rate
        return self.job_post.budget_amount
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_accepted(self):
        return self.status == 'accepted'


# Optional: Job Review model for after completion
class JobReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    job_post = models.OneToOneField(
        JobPost,
        on_delete=models.CASCADE,
        related_name='review'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    reviewed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_reviews'
    )
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.rating} stars from {self.reviewer.username} to {self.reviewed.username}"