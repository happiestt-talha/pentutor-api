# course/serializers.py

from rest_framework import serializers
from .models import Course, Video, Quiz, Assignment, Enrollment, Progress
from authentication.models import User,TeacherProfile,StudentProfile
from support_feedback.models import CourseFeedback



class TeacherSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    profile_picture = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)
    expertise_areas = serializers.JSONField(required=True)
    education = serializers.JSONField(required=True)
    languages_spoken = serializers.JSONField(required=True)
    availability_schedule = serializers.JSONField(required=True)
    preferred_teaching_methods = serializers.JSONField(required=True)
    course_categories = serializers.JSONField(required=True)
    
    class Meta:
        model = TeacherProfile
        fields = ['id', 'username', 'first_name', 'last_name', 'bio', 'profile_picture','email','expertise_areas','education'
                  ,'languages_spoken','availability_schedule','preferred_teaching_methods','course_categories']
    
    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return self.context['request'].build_absolute_uri(obj.profile_picture.url)
        return None


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'video_file', 'duration', 'order', 'created_at']


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'passing_score', 'order']


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'description', 'due_date', 'order']


class CourseListSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(read_only=True)
    total_videos = serializers.SerializerMethodField()
    total_enrollments = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'teacher', 'price', 
            'course_type', 'thumbnail', 'created_at', 'is_active',
            'total_videos', 'total_enrollments'
        ]
    
    def get_total_videos(self, obj):
        return obj.get_total_videos()
    
    def get_total_enrollments(self, obj):
        return obj.get_total_enrollments()


class CourseDetailSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(read_only=True)
    videos = VideoSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    total_videos = serializers.SerializerMethodField()
    total_enrollments = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'teacher', 'price', 
            'course_type', 'thumbnail', 'created_at', 'is_active',
            'videos', 'quizzes', 'assignments', 'total_videos', 'total_enrollments','reviews'
        ]
    
    def get_total_videos(self, obj):
        return obj.get_total_videos()
    
    def get_total_enrollments(self, obj):
        return obj.get_total_enrollments()
    
    def get_reviews(self, obj):
        feedbacks = obj.reviews.all()
        serializer = CourseFeedbackSerializer(
            feedbacks, many=True, context=self.context
        )
        return serializer.data


class VideoDetailSerializer(serializers.ModelSerializer):
    quizzes = QuizSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'video_file', 'duration', 
            'order', 'created_at', 'course_title', 'quizzes', 'assignments'
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'is_completed']


class ProgressSerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source='video.title', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    
    class Meta:
        model = Progress
        fields = [
            'id', 'course', 'video', 'quiz', 'assignment', 
            'completed_at', 'video_title', 'quiz_title', 'assignment_title'
        ]

class CourseFeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = CourseFeedback
        fields = [
            'id', 'user_name', 'first_name', 'last_name',
            'profile_picture', 'rating', 'feedback_text', 'created_at'
        ]

    def get_profile_picture(self, obj):
        # StudentProfile ka relation nikalke image ka URL dena
        student_profile = getattr(obj.user, 'student_profile', None)
        if student_profile and student_profile.profile_picture:
            return self.context['request'].build_absolute_uri(student_profile.profile_picture.url)
        return None
