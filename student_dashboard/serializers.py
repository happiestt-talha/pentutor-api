# student_dashboard/serializers.py

from rest_framework import serializers
from courses.models import Enrollment, Progress
from courses.serializers import CourseListSerializer


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'is_completed']


class StudentProgressSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    
    class Meta:
        model = Progress
        fields = [
            'id', 'course_title', 'video_title', 'quiz_title', 
            'assignment_title', 'completed_at'
        ]