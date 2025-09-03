# job_board/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import JobPost, JobApplication, JobReview
from authentication.models import StudentProfile, TeacherProfile
from courses.models import Course


class CourseBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'course_type']


class StudentBasicSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'username', 'full_name','profile_picture']
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            # Return absolute URL for frontend usage
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None
         


class TeacherBasicSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherProfile
        fields = ['id', 'username', 'full_name','profile_picture']
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            # Return absolute URL for frontend usage
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None


class JobPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = [
            'title', 'description', 'course', 'subject_text', 'teaching_mode',
            'budget_amount', 'budget_type', 'duration_value', 'duration_unit',
            'additional_notes', 'location', 'deadline'
        ]
    
    def validate(self, data):
        # # Ensure either course or subject_text is provided
        # if not data.get('course') and not data.get('subject_text'):
        #     raise serializers.ValidationError(
        #         "Either select a course or provide subject text."
        #     )
        
        # Validate location for physical teaching
        if data.get('teaching_mode') == 'physical' and not data.get('location'):
            raise serializers.ValidationError(
                "Location is required for physical teaching mode."
            )
        
        # Validate deadline is in future
        if data.get('deadline') and data.get('deadline') <= timezone.now():
            raise serializers.ValidationError(
                "Deadline must be in the future."
            )
        
        return data
    
    def create(self, validated_data):
        # Set student from request user
        request = self.context.get('request')
        print(hasattr(request.user, 'student_profile'))
        if request and hasattr(request.user, 'student_profile'):
            print(request.user.student_profile)
            return JobPost.objects.create(student=request.user.student_profile, **validated_data)
        raise serializers.ValidationError("Only students can create job posts.")


class JobPostListSerializer(serializers.ModelSerializer):
    student = StudentBasicSerializer(read_only=True)
    course = CourseBasicSerializer(read_only=True)
    subject_display = serializers.CharField(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'description', 'student', 'course', 'subject_display',
            'teaching_mode', 'budget_amount', 'budget_type', 'duration_value',
            'duration_unit', 'location', 'status', 'applications_count',
            'created_at', 'time_ago', 'deadline'
        ]
    
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"
   
class JobPostDetailSerializer(serializers.ModelSerializer):
    student = StudentBasicSerializer(read_only=True)
    course = CourseBasicSerializer(read_only=True)
    subject_display = serializers.CharField(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    selected_teacher = TeacherBasicSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()
    can_apply = serializers.SerializerMethodField()
    user_application = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'description', 'student', 'course', 'subject_display',
            'teaching_mode', 'budget_amount', 'budget_type', 'duration_value',
            'duration_unit', 'additional_notes', 'location', 'status',
            'applications_count', 'selected_teacher', 'created_at', 'updated_at',
            'deadline', 'is_owner', 'can_apply', 'user_application'
        ]
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            return obj.student == request.user.student_profile
        return False
    
    def get_can_apply(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'teacher_profile'):
            return False
        
        # Check if job is open and teacher hasn't applied yet
        if obj.status != 'open':
            return False
        
        return not obj.applications.filter(
            teacher=request.user.teacher_profile
        ).exists()
    
    def get_user_application(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'teacher_profile'):
            try:
                application = obj.applications.get(
                    teacher=request.user.teacher_profile
                )
                return JobApplicationBasicSerializer(application).data
            except JobApplication.DoesNotExist:
                pass
        return None


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['cover_letter', 'proposed_rate']
    
    def validate_proposed_rate(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Proposed rate must be positive.")
        return value
    
    def create(self, validated_data):
        # Set teacher and job_post from context
        request = self.context.get('request')
        job_post = self.context.get('job_post')
        
        if request and hasattr(request.user, 'teacher_profile'):
            validated_data['teacher'] = request.user.teacher_profile
        
        if job_post:
            validated_data['job_post'] = job_post
        
        return super().create(validated_data)


class JobApplicationBasicSerializer(serializers.ModelSerializer):
    teacher = TeacherBasicSerializer(read_only=True)
    final_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'teacher', 'cover_letter', 'proposed_rate', 'final_rate',
            'status', 'applied_at', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.applied_at
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    teacher = TeacherBasicSerializer(read_only=True)
    job_post = JobPostListSerializer(read_only=True)
    final_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_post', 'teacher', 'cover_letter', 'proposed_rate',
            'final_rate', 'status', 'applied_at', 'updated_at'
        ]


class JobApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['status']
    
    def validate_status(self, value):
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "Status can only be updated to 'accepted' or 'rejected'."
            )
        return value


class JobPostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = ['status']
    
    def validate_status(self, value):
        allowed_statuses = ['in_progress', 'completed', 'cancelled']
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Status can only be updated to: {', '.join(allowed_statuses)}"
            )
        return value


class JobReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    reviewed_name = serializers.CharField(source='reviewed.username', read_only=True)
    
    class Meta:
        model = JobReview
        fields = [
            'id', 'rating', 'comment', 'reviewer_name', 'reviewed_name', 'created_at'
        ]
        read_only_fields = ['reviewer', 'reviewed']
    
    def create(self, validated_data):
        request = self.context.get('request')
        job_post = self.context.get('job_post')
        
        if request:
            validated_data['reviewer'] = request.user
            # Set reviewed user based on who's reviewing
            if hasattr(request.user, 'studentprofile'):
                # Student reviewing teacher
                validated_data['reviewed'] = job_post.selected_teacher.user
            else:
                # Teacher reviewing student
                validated_data['reviewed'] = job_post.student.user
        
        validated_data['job_post'] = job_post
        return super().create(validated_data)


# Dashboard serializers for overview
class MyJobPostSerializer(serializers.ModelSerializer):
    course = CourseBasicSerializer(read_only=True)
    subject_display = serializers.CharField(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    selected_teacher = TeacherBasicSerializer(read_only=True)
    
    class Meta:
        model = JobPost
        fields = [
            'id', 'title', 'course', 'subject_display', 'status',
            'applications_count', 'selected_teacher', 'created_at',
            'budget_amount', 'budget_type'
        ]


class MyJobApplicationSerializer(serializers.ModelSerializer):
    job_post = JobPostListSerializer(read_only=True)
    final_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_post', 'status', 'final_rate', 'applied_at'
        ]