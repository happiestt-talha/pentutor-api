# course/model.py

from django.db import models

from django.utils import timezone
from authentication.models import TeacherProfile,StudentProfile,User

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    profile_pic = models.ImageField(upload_to='teacher_pics/', blank=True)
    
    def __str__(self):
        return self.user.username

class Course(models.Model):
    COURSE_TYPES = [
        ('free', 'Free'),
        ('paid', 'Paid'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    has_live_classes = models.BooleanField(default=False)
    live_class_schedule = models.JSONField(default=dict, blank=True)
    course_type = models.CharField(max_length=10, choices=COURSE_TYPES, default='free')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    def get_total_videos(self):
        return self.videos.count()
    
    def get_total_enrollments(self):
        return self.enrollments.count()
    
    def get_live_classes(self):
        from meetings.models import Meeting
        return Meeting.objects.filter(course=self, meeting_type='lecture')

    def has_user_paid(self, user):

        if self.course_type == 'free':
            return True
        
        from payments.models import Payment
        return Payment.objects.filter(
            user=user,
            course=self,
            is_successful=True
        ).exists()



# NEW MODEL: Topic
class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    def get_total_videos(self):
        return self.videos.count()
    
    def get_total_duration(self):
        # Calculate total duration of all videos in this topic
        videos = self.videos.all()
        total_minutes = 0
        for video in videos:
            if video.duration:
                # Assuming duration is in format "10:30"
                try:
                    minutes, seconds = map(int, video.duration.split(':'))
                    total_minutes += minutes + (seconds / 60)
                except:
                    pass
        return f"{int(total_minutes)}:{int((total_minutes % 1) * 60):02d}"


class Video(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='videos')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='videos', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='course_videos/')
    duration = models.CharField(max_length=10, blank=True)  # Format: "10:30"
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    passing_score = models.IntegerField(default=70)
    order = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    options = models.JSONField()
    correct_answer = models.IntegerField()
    explanation = models.TextField(blank=True)

    def __str__(self):
        return self.question[:50]


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)  
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    payment_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('verified', 'Verified')], null=True,blank=True)
    enrolled_at = models.DateTimeField(default=timezone.now)
    is_completed = models.BooleanField(default=False)
    class Meta:
        unique_together = ['student', 'course']  # Prevent duplicate enrollments
    
    def __str__(self):
        return f"{self.student.full_name} - Enrollment in {self.course.title}"

class Progress(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE) 
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    completed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['student', 'course', 'video', 'quiz', 'assignment']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"