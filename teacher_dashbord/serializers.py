# teacher_dashboard/serializers.py

from rest_framework import serializers
from courses.models import Course, Video, Quiz, Assignment, Enrollment , Question,Topic

from meetings.models import Meeting


class TeacherCourseSerializer(serializers.ModelSerializer):
    total_videos = serializers.SerializerMethodField()
    total_enrollments = serializers.SerializerMethodField()
    total_quizzes = serializers.SerializerMethodField()
    total_live_classes = serializers.SerializerMethodField() 
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'price', 'course_type', 
            'thumbnail', 'created_at', 'is_active', 'total_videos', 
            'total_enrollments', 'total_quizzes','has_live_classes',  
            'total_live_classes'
        ]
        read_only_fields = ['id', 'created_at', 'total_videos', 'total_enrollments', 'total_quizzes','total_live_classes']
    
    def get_total_videos(self, obj):
        return obj.videos.count()
    
    def get_total_live_classes(self, obj):
        return obj.get_live_classes().count()
    
    def get_total_enrollments(self, obj):
        return obj.enrollments.count()
    
    def get_total_quizzes(self, obj):
        return obj.quizzes.count()


class TeacherVideoSerializer(serializers.ModelSerializer):
    has_quiz = serializers.SerializerMethodField()
    has_assignment = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'title','topic', 'description', 'video_file', 'duration', 
            'order', 'created_at', 'has_quiz', 'has_assignment'
        ]
        read_only_fields = ['id', 'created_at', 'has_quiz', 'has_assignment']
    
    def get_has_quiz(self, obj):
        return obj.quizzes.exists()
    
    def get_has_assignment(self, obj):
        return obj.assignments.exists()


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question', 'options', 'correct_answer', 'explanation']




class TeacherQuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)
    class Meta:
        model = Quiz
        fields = [
            'id', 'title','topic', 'description', 'passing_score', 'order', 'video', 'questions'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        quiz = Quiz.objects.create(**validated_data)
        for question_data in questions_data:
            Question.objects.create(quiz=quiz, **question_data)
        return quiz

class EnrolledStudentSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'course_title', 'enrolled_at', 'is_completed'
            'student_username', 'student_email'  # Add these when student model is ready
        ]
        read_only_fields = ['id', 'enrolled_at', 'course_title']




class LiveClassSerializer(serializers.ModelSerializer):
    total_participants = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    
    class Meta:
        model = Meeting
        fields = [
            'id', 'meeting_id', 'title', 'scheduled_time', 'status',
            'max_participants', 'total_participants', 'can_join',
            'is_recorded', 'recording_url', 'created_at'
        ]
        read_only_fields = ['id', 'meeting_id', 'total_participants', 'can_join']
    
    def get_total_participants(self, obj):
        return obj.participants.filter(left_at__isnull=True).count()
    
    def get_can_join(self, obj):
        return obj.status in ['waiting', 'active']
    



class TeacherTopicSerializer(serializers.ModelSerializer):
    total_videos = serializers.ReadOnlyField(source='get_total_videos')
    total_duration = serializers.ReadOnlyField(source='get_total_duration')
    course_title = serializers.ReadOnlyField(source='course.title')
    
    class Meta:
        model = Topic
        fields = [
            'id', 
            'title', 
            'description', 
            'order', 
            'created_at', 
            'is_active',
            'total_videos',
            'total_duration',
            'course_title'
        ]
        read_only_fields = ['id', 'created_at', 'course_title']
    
    def validate_order(self, value):
        """Ensure order is positive"""
        if value < 0:
            raise serializers.ValidationError("Order must be a positive number.")
        return value
    
    def validate_title(self, value):
        """Ensure title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

class TeacherAssignmentSerializer(serializers.ModelSerializer):
    course_title = serializers.ReadOnlyField(source='course.title')
    topic_title = serializers.ReadOnlyField(source='topic.title')
    
    class Meta:
        model = Assignment
        fields = [
            'id', 
            'title', 
            'description', 
            'due_date', 
            'order',
            'course_title',
            'topic_title'
        ]
        read_only_fields = ['id', 'course_title', 'topic_title']