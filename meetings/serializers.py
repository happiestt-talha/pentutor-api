# meeting/serializers.py

from rest_framework import serializers
from .models import Meeting, Participant, MeetingRecording, MeetingChat
from authentication.serializers import UserSerializer
from courses.serializers import CourseListSerializer

class MeetingSerializer(serializers.ModelSerializer):
    """Meeting serializer with host info"""
    host = UserSerializer(read_only=True)
    course = CourseListSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    
    class Meta:
        model = Meeting
        fields = [
            'id', 'meeting_id', 'title', 'password', 'meeting_type', 
            'status', 'host', 'course', 'max_participants', 'is_waiting_room_enabled',
            'allow_participant_share_screen', 'allow_participant_unmute',
            'enable_chat', 'enable_reactions', 'is_recorded', 'recording_url',
            'recording_duration', 'scheduled_time', 'started_at', 'ended_at', 
            'created_at', 'participants_count', 'is_active', 'can_join'
        ]
        read_only_fields = [
            'id', 'meeting_id', 'password', 'host', 'status', 
            'started_at', 'ended_at', 'created_at'
        ]
    
    def get_participants_count(self, obj):
        """Get count of active participants"""
        return obj.participants.filter(left_at__isnull=True).count()
    
    def get_is_active(self, obj):
        """Check if meeting is currently active"""
        return obj.status == 'active'
    
    def get_can_join(self, obj):
        """Check if current user can join the meeting"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_join, message = obj.can_user_join(request.user)
            return {'can_join': can_join, 'message': message}
        return {'can_join': False, 'message': 'Authentication required'}


class ParticipantSerializer(serializers.ModelSerializer):
    """Participant serializer with user info"""
    user = UserSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = Participant
        fields = [
            'id', 'user', 'guest_name', 'role', 'is_muted', 'is_video_on', 
            'is_hand_raised', 'is_sharing_screen', 'joined_at', 
            'left_at', 'is_active', 'duration_minutes'
        ]
        read_only_fields = [
            'id', 'user', 'joined_at', 'left_at'
        ]
    
    def get_is_active(self, obj):
        """Check if participant is currently in meeting"""
        return obj.left_at is None
    
    def get_duration_minutes(self, obj):
        """Calculate how long participant has been in meeting"""
        if obj.left_at:
            duration = obj.left_at - obj.joined_at
        else:
            from django.utils import timezone
            duration = timezone.now() - obj.joined_at
        return int(duration.total_seconds() / 60)


class CreateMeetingSerializer(serializers.Serializer):
    """Serializer for creating new meeting"""
    title = serializers.CharField(max_length=200, required=True)
    meeting_type = serializers.ChoiceField(
        choices=['instant', 'scheduled', 'lecture'], 
        default='instant'
    )
    access_type = serializers.ChoiceField(
        choices=['public', 'private', 'approval_required'],
        default='public'
    )
    course_id = serializers.UUIDField(required=False)
    scheduled_time = serializers.DateTimeField(required=False)
    max_participants = serializers.IntegerField(default=100, min_value=2, max_value=500)
    waiting_room = serializers.BooleanField(default=False)
    allow_unmute = serializers.BooleanField(default=True)
    allow_screen_share = serializers.BooleanField(default=True)
    enable_chat = serializers.BooleanField(default=True)
    enable_reactions = serializers.BooleanField(default=True)
    is_recorded = serializers.BooleanField(default=False)
    password = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_password_required = serializers.BooleanField(default=False)
    invites = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
        help_text="List of email addresses to invite (for private meetings)"
    )
    
    def validate_scheduled_time(self, value):
        """Validate scheduled time is in future"""
        if value:
            from django.utils import timezone
            if value <= timezone.now():
                raise serializers.ValidationError(
                    "Scheduled time must be in the future"
                )
        return value
    
    def validate_course_id(self, value):
        """Validate course exists and user is teacher"""
        if value:
            from courses.models import Course
            try:
                course = Course.objects.get(id=value)
                request = self.context.get('request')
                if request and request.user != course.teacher.user:
                    raise serializers.ValidationError(
                        "You can only create meetings for your own courses"
                    )
                return value
            except Course.DoesNotExist:
                raise serializers.ValidationError("Course not found")
        return value
    
    def validate(self, data):
        """Validate meeting data"""
        if data.get('meeting_type') == 'scheduled' and not data.get('scheduled_time'):
            raise serializers.ValidationError(
                "Scheduled time is required for scheduled meetings"
            )
        
        if data.get('meeting_type') == 'lecture' and not data.get('course_id'):
            raise serializers.ValidationError(
                "Course is required for lecture meetings"
            )
        if data.get('access_type') == 'private' and not data.get('invites'):
            raise serializers.ValidationError(
                "Invites are required for private meetings"
            )
        
        return data


class JoinMeetingSerializer(serializers.Serializer):
    """Serializer for joining meeting"""
    meeting_id = serializers.UUIDField(required=True)
    password = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_meeting_id(self, value):
        """Validate meeting exists and is joinable"""
        try:
            meeting = Meeting.objects.get(meeting_id=value)
            if meeting.status == 'ended':
                raise serializers.ValidationError("Meeting has ended")
            return value
        except Meeting.DoesNotExist:
            raise serializers.ValidationError("Meeting not found")
    
    def validate(self, data):
        """Validate join request"""
        try:
            meeting = Meeting.objects.get(meeting_id=data['meeting_id'])
            
            # Check password if meeting has one
            if meeting.password and data.get('password') != meeting.password:
                raise serializers.ValidationError("Invalid meeting password")
            
            # Check if user can join (payment, enrollment, etc.)
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                can_join, message = meeting.can_user_join(request.user)
                if not can_join:
                    raise serializers.ValidationError(message)
            
            data['meeting'] = meeting
            return data
        except Meeting.DoesNotExist:
            raise serializers.ValidationError("Meeting not found")


class MeetingRecordingSerializer(serializers.ModelSerializer):
    """Serializer for meeting recordings"""
    meeting_title = serializers.CharField(source='meeting.title', read_only=True)
    meeting_id = serializers.CharField(source='meeting.meeting_id', read_only=True)
    
    class Meta:
        model = MeetingRecording
        fields = [
            'id', 'meeting_title', 'meeting_id', 'file_path', 
            'file_size', 'duration', 'is_processed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MeetingChatSerializer(serializers.ModelSerializer):
    """Serializer for meeting chat messages"""
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = MeetingChat
        fields = ['id', 'sender', 'message', 'timestamp']
        read_only_fields = ['id', 'sender', 'timestamp']


class SendChatMessageSerializer(serializers.Serializer):
    """Serializer for sending chat messages"""
    meeting_id = serializers.UUIDField(required=True)
    message = serializers.CharField(max_length=1000, required=True)
    
    def validate_meeting_id(self, value):
        """Validate meeting exists and is active"""
        try:
            meeting = Meeting.objects.get(meeting_id=value)
            if meeting.status != 'active':
                raise serializers.ValidationError("Meeting is not active")
            if not meeting.enable_chat:
                raise serializers.ValidationError("Chat is disabled for this meeting")
            return value
        except Meeting.DoesNotExist:
            raise serializers.ValidationError("Meeting not found")


class ReactionSerializer(serializers.Serializer):
    """Serializer for adding reactions"""
    meeting_id = serializers.UUIDField(required=True)
    reaction_type = serializers.ChoiceField(
        choices=['like', 'love', 'clap', 'laugh', 'wow', 'sad'],
        required=True
    )
    
    def validate_meeting_id(self, value):
        """Validate meeting exists and reactions are enabled"""
        try:
            meeting = Meeting.objects.get(meeting_id=value)
            if meeting.status != 'active':
                raise serializers.ValidationError("Meeting is not active")
            if not meeting.enable_reactions:
                raise serializers.ValidationError("Reactions are disabled for this meeting")
            return value
        except Meeting.DoesNotExist:
            raise serializers.ValidationError("Meeting not found")


class CourseLectureSerializer(serializers.ModelSerializer):
    """Serializer for course lecture meetings"""
    host = UserSerializer(read_only=True)
    course = CourseListSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Meeting
        fields = [
            'id', 'meeting_id', 'title', 'host', 'course', 'status',
            'is_recorded', 'recording_url', 'recording_duration',
            'scheduled_time', 'started_at', 'ended_at', 'participants_count'
        ]
    
    def get_participants_count(self, obj):
        """Get count of participants who attended"""
        return obj.participants.count()