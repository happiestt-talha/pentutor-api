# authetication/model.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.conf import settings

class User(AbstractUser):
    USER_ROLES = [
        ('user','User'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('subadmin', 'SubAdmin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table = 'users'


class StudentProfile(models.Model):
    EDUCATION_LEVELS = [
        ('high_school', 'High School'),
        ('bachelors', "Bachelor's Degree"),
        ('masters', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other')
    ]

    EMPLOYMENT_STATUS = [
        ('student', 'Full-time Student'),
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('unemployed', 'Looking for Opportunities'),
        ('other', 'Other')
    ]

    # Base Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    email = models.EmailField(unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    
    # Education and Skills
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVELS, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    enrollment_number = models.CharField(max_length=100, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    gpa = models.FloatField(blank=True, null=True)
    skills = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    
    # Career
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, blank=True)
    current_job_title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    career_goals = models.TextField(blank=True)
    
    # Course Related
    enrolled_courses = models.ManyToManyField('courses.Course', through='courses.Enrollment', related_name='enrolled_students')
    completed_courses_count = models.PositiveIntegerField(default=0)
    current_courses_count = models.PositiveIntegerField(default=0)
    attendance_percentage = models.FloatField(default=0.0)
    completed_assignments = models.PositiveIntegerField(default=0)
    certificates = models.JSONField(default=list, blank=True)
    average_course_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    
    # Social and Portfolio
    linkedin_profile = models.URLField(blank=True)
    github_profile = models.URLField(blank=True)
    portfolio_website = models.URLField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    
    # Preferences
    preferred_learning_time = models.JSONField(default=list, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    language_preferences = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student: {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['education_level', 'graduation_year']),
            models.Index(fields=['employment_status']),
        ]




class TeacherProfile(models.Model):
    EXPERTISE_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
        ('master', 'Master')
    ]

    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance')
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]


    # Base Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    email = models.EmailField(unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)

    # Professional Information
    employee_id = models.CharField(max_length=100, blank=True, null=True)
    headline = models.CharField(max_length=200,null=True,blank=True)
    expertise_areas = models.JSONField(default=list)
    expertise_level = models.CharField(max_length=20, choices=EXPERTISE_LEVELS,default='expert')
    years_of_experience = models.PositiveIntegerField(default=0)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE,default='part_time')
    department = models.CharField(max_length=100, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Documents
    resume = models.FileField(upload_to='teacher_documents/resumes/', null=True, blank=True)
    degree_certificates = models.FileField(upload_to='teacher_documents/degrees/', null=True, blank=True)
    id_proof = models.FileField(upload_to='teacher_documents/id_proofs/', null=True, blank=True)    

    # Qualifications
    education = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    awards = models.JSONField(default=list)
    publications = models.JSONField(default=list)
    
    # Course Related
    courses_created = models.ManyToManyField('courses.Course', related_name='instructors',blank=True)
    total_courses = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    teaching_style = models.TextField(blank=True)
    languages_spoken = models.JSONField(default=list)
    
    # Professional Links
    linkedin_profile = models.URLField(blank=True)
    github_profile = models.URLField(blank=True)
    personal_website = models.URLField(blank=True)
    youtube_channel = models.URLField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    
    # Availability and Preferences
    availability_schedule = models.JSONField(default=dict)
    preferred_teaching_methods = models.JSONField(default=list)
    course_categories = models.JSONField(default=list)
    notification_preferences = models.JSONField(default=dict)
    # Status and Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # Statistics
    total_course_hours = models.PositiveIntegerField(default=0)
    total_students_helped = models.PositiveIntegerField(default=0)
    response_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    average_response_time = models.DurationField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Teacher: {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['expertise_level', 'years_of_experience']),
            models.Index(fields=['average_rating']),
             models.Index(fields=['status']),
        ]



class StudentQuery(models.Model):
    """
    Student Query Form - for visitors who want to inquire before registration
    """
    # Basic Info
    name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_no = models.CharField(max_length=15)
    area = models.CharField(max_length=100)
    current_class = models.CharField(max_length=50, help_text="Current class/grade")
    
    # Academic Info
    subjects = models.TextField(help_text="Subjects of interest (comma separated)")
    special_requirements = models.TextField(blank=True, null=True, help_text="Any special requirements or requests")
    
    # Status
    is_registered = models.BooleanField(default=False, help_text="Has this person registered as a student?")
    is_processed = models.BooleanField(default=False, help_text="Has admin processed this query?")
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes for this query")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to user if they register later
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User account if they registered later"
    )

    def __str__(self):
        return f"Query by {self.name} - {self.email}"

    class Meta:
        db_table = 'student_queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_registered']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['created_at']),
        ]

