# course/serializers.py

from rest_framework import serializers
from .models import Course, Video, Quiz, Assignment, Enrollment, Progress,Topic
from authentication.models import User,TeacherProfile,StudentProfile
from support_feedback.models import CourseFeedback
from support_feedback.models import TeacherFeedback
from support_feedback.serializers import TeacherFeedbackSerializer

class CourseSerializer(serializers.ModelSerializer):
    total_students = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'total_students']

    def get_total_students(self, obj):
        if hasattr(obj, 'enrolled_students'):
            return obj.enrolled_students.count()
        return 0

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
    total_courses = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    feedbacks = TeacherFeedbackSerializer(many=True, read_only=True)
    courses_created = CourseSerializer(many=True, read_only=True)
    
    class Meta:
        model = TeacherProfile
        fields = ['id', 'username', 'first_name', 'last_name','age', 'bio', 'gender','date_of_birth','phone','address','city','country','headline','expertise_level','years_of_experience','employment_type','department',
                  'hourly_rate','total_courses','total_students','average_rating','teaching_style','courses_created','profile_picture','email','expertise_areas','education'
                  ,'languages_spoken','availability_schedule','preferred_teaching_methods','course_categories','feedbacks','created_at']
    
    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return self.context['request'].build_absolute_uri(obj.profile_picture.url)
        return None
    
    def get_total_courses(self, obj):
        return obj.courses_created.count()

    def get_total_students(self, obj):
        # assume har course me enrolled_students M2M field hoga
        students = set()
        for course in obj.courses_created.all():
            if hasattr(course, 'enrolled_students'):
                students.update(course.enrolled_students.values_list('id', flat=True))
        return len(students)


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
    thumbnail = serializers.SerializerMethodField()
    
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
    
    def get_thumbnail(self, obj):
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None

class TopicSerializer(serializers.ModelSerializer):
    video_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            'id', 'title', 'description', 'order', 
            'video_count', 'total_duration', 'is_active'
        ]
    
    def get_video_count(self, obj):
        return obj.videos.count()
    
    def get_total_duration(self, obj):
        return obj.get_total_duration()


class VideoWithTopicSerializer(serializers.ModelSerializer):
    topic_title = serializers.CharField(source='topic.title', read_only=True)
    has_quiz = serializers.SerializerMethodField()
    has_assignment = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'duration', 'order',
            'topic_title', 'has_quiz', 'has_assignment'
        ]
    
    def get_has_quiz(self, obj):
        return obj.quizzes.exists()
    
    def get_has_assignment(self, obj):
        return obj.assignments.exists()


class TopicDetailSerializer(serializers.ModelSerializer):
    videos = VideoWithTopicSerializer(many=True, read_only=True)
    video_count = serializers.SerializerMethodField()
    quiz_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            'id', 'title', 'description', 'order', 'created_at',
            'videos', 'video_count', 'quiz_count', 'assignment_count'
        ]
    
    def get_video_count(self, obj):
        return obj.videos.count()
    
    def get_quiz_count(self, obj):
        return obj.quizzes.count()
    
    def get_assignment_count(self, obj):
        return obj.assignments.count()


class CourseWithTopicsSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.username', read_only=True)
    total_videos = serializers.SerializerMethodField()
    total_topics = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'course_type',
            'thumbnail', 'teacher_name', 'total_videos', 'total_topics',
            'topics', 'created_at', 'has_live_classes'
        ]
    
    def get_total_videos(self, obj):
        return obj.get_total_videos()
    
    def get_total_topics(self, obj):
        return obj.get_total_topics()



class CourseDetailSerializer(serializers.ModelSerializer):
    topics = TopicDetailSerializer(many=True, read_only=True)
    teacher = TeacherSerializer(read_only=True)
    videos = VideoSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    total_videos = serializers.SerializerMethodField()
    total_enrollments = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'teacher', 'price', 
            'course_type', 'thumbnail', 'topics','created_at', 'is_active',
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
    def get_thumbnail(self, obj):
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None


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
