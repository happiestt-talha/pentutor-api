# notifications/serializers.py

from rest_framework import serializers
from .models import Notification
from courses.models import Course, Video, Quiz
from meetings.models import Meeting
from authentication.models import User


class SenderSerializer(serializers.ModelSerializer):
    """Serializer for the user who sent the notification"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class NotificationCourseSerializer(serializers.ModelSerializer):
    """Basic course serializer for notifications"""
    class Meta:
        model = Course
        fields = ['id', 'title', 'course_type']


class NotificationVideoSerializer(serializers.ModelSerializer):
    """Basic video serializer for notifications"""
    class Meta:
        model = Video
        fields = ['id', 'title', 'duration']


class NotificationQuizSerializer(serializers.ModelSerializer):
    """Basic quiz serializer for notifications"""
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'passing_score']


class MeetingSerializer(serializers.ModelSerializer):
    """Basic meeting serializer for notifications"""
    class Meta:
        model = Meeting
        fields = ['id', 'title', 'scheduled_time', 'meeting_type']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model with nested related objects
    """
    sender = SenderSerializer(read_only=True)
    course = NotificationCourseSerializer(read_only=True)
    video = NotificationVideoSerializer(read_only=True)
    quiz = NotificationQuizSerializer(read_only=True)
    meeting = MeetingSerializer(read_only=True)
    time_since_created = serializers.ReadOnlyField()
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'sender',
            'course',
            'video',
            'quiz',
            'meeting',
            'is_read',
            'created_at',
            'read_at',
            'time_since_created'
        ]
        read_only_fields = [
            'id',
            'created_at',
            'read_at',
            'time_since_created'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for notification lists (without nested objects)
    """
    sender_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    time_since_created = serializers.ReadOnlyField()
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'sender_name',
            'course_title',
            'is_read',
            'created_at',
            'time_since_created'
        ]
    
    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username
        return None
    
    def get_course_title(self, obj):
        if obj.course:
            return obj.course.title
        return None


class MarkAsReadSerializer(serializers.Serializer):
    """
    Serializer for marking notifications as read
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of notification IDs to mark as read"
    )
    
    def validate_notification_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one notification ID is required.")
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics
    """
    total_count = serializers.IntegerField(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    notification_types = serializers.DictField(read_only=True)